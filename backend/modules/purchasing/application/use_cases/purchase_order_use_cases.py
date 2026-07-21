"""Purchase Order use cases: create (with line items) against an active
Supplier, edit while still draft, change status through the manual stages
(sent/confirmed/cancelled), and receive against a line -- which accumulates
`quantity_received`, optionally creates a real `catalog_slabs` row (reusing
Catalog's own CreateSlabUseCase, the same cross-module-reuse pattern
Production uses for slab status changes), and recomputes the order's overall
status (partially_received/received) as a side effect, never manually.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import CreateSlabInput
from modules.catalog.application.use_cases import CreateSlabUseCase
from modules.catalog.infrastructure.repositories.material_repository import MaterialRepository
from modules.purchasing.application.dtos import (
    CreatePurchaseOrderInput,
    ReceivePurchaseOrderLineInput,
    UpdatePurchaseOrderInput,
    UpdatePurchaseOrderStatusInput,
)
from modules.purchasing.domain import events as purchasing_events
from modules.purchasing.domain.exceptions import (
    EmptyPurchaseOrderError,
    InvalidPurchaseOrderTransitionError,
    InvalidReceiptQuantityError,
    PurchaseOrderImmutableError,
    PurchaseOrderNotReceivableError,
    ReceivedLineHasNoMaterialError,
    SupplierInactiveError,
)
from modules.purchasing.domain.value_objects import (
    PO_STATUS_CANCELLED,
    PO_STATUS_DRAFT,
    PO_STATUS_PARTIALLY_RECEIVED,
    PO_STATUS_RECEIVED,
    PURCHASE_ORDER_STATUSES_EDITABLE,
    PURCHASE_ORDER_STATUSES_RECEIVABLE,
    SUPPLIER_STATUS_ACTIVE,
    is_valid_purchase_order_transition,
)
from modules.purchasing.infrastructure.models.goods_receipt import GoodsReceipt
from modules.purchasing.infrastructure.models.purchase_order import PurchaseOrder
from modules.purchasing.infrastructure.models.purchase_order_line import PurchaseOrderLine
from modules.purchasing.infrastructure.repositories.goods_receipt_repository import GoodsReceiptRepository
from modules.purchasing.infrastructure.repositories.purchase_order_line_repository import (
    PurchaseOrderLineRepository,
)
from modules.purchasing.infrastructure.repositories.purchase_order_repository import PurchaseOrderRepository
from modules.purchasing.infrastructure.repositories.supplier_repository import SupplierRepository

MODULE = "purchasing"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreatePurchaseOrderUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.purchase_orders = PurchaseOrderRepository(db)
        self.lines = PurchaseOrderLineRepository(db)
        self.suppliers = SupplierRepository(db)

    def execute(self, data: CreatePurchaseOrderInput) -> PurchaseOrder:
        supplier = self.suppliers.get(company_id=data.company_id, supplier_id=data.supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier not found")
        if supplier.status != SUPPLIER_STATUS_ACTIVE:
            raise SupplierInactiveError(f"Supplier '{supplier.name}' is hidden and cannot receive new orders")
        if not data.lines:
            raise EmptyPurchaseOrderError("A purchase order needs at least one line item")

        year = _now().year
        po_number = self.purchase_orders.next_po_number(company_id=data.company_id, year=year)

        subtotal = Decimal("0")
        for line in data.lines:
            subtotal += line.quantity * line.unit_cost

        purchase_order = PurchaseOrder(
            company_id=data.company_id,
            supplier_id=supplier.id,
            po_number=po_number,
            status=PO_STATUS_DRAFT,
            currency=data.currency,
            notes=data.notes,
            expected_delivery_date=data.expected_delivery_date,
            subtotal_amount=subtotal,
            total_amount=subtotal,
            created_by=data.actor_user_id,
        )
        self.purchase_orders.add(purchase_order)

        for sort_order, line in enumerate(data.lines):
            self.lines.add(
                PurchaseOrderLine(
                    company_id=data.company_id,
                    purchase_order_id=purchase_order.id,
                    material_id=line.material_id,
                    description=line.description,
                    quantity=line.quantity,
                    unit=line.unit,
                    unit_cost=line.unit_cost,
                    line_total=line.quantity * line.unit_cost,
                    sort_order=sort_order,
                )
            )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="purchase_order.created",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            diff={"po_number": po_number, "supplier_id": str(supplier.id), "line_count": len(data.lines)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=purchasing_events.PURCHASE_ORDER_CREATED,
                company_id=data.company_id,
                payload={
                    "purchase_order_id": str(purchase_order.id),
                    "po_number": po_number,
                    "supplier_id": str(supplier.id),
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return purchase_order


class UpdatePurchaseOrderUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.purchase_orders = PurchaseOrderRepository(db)

    def execute(self, data: UpdatePurchaseOrderInput) -> PurchaseOrder:
        purchase_order = self.purchase_orders.get(company_id=data.company_id, purchase_order_id=data.purchase_order_id)
        if purchase_order is None:
            raise NotFoundError("Purchase order not found")
        if purchase_order.status not in PURCHASE_ORDER_STATUSES_EDITABLE:
            raise PurchaseOrderImmutableError(
                f"Purchase order '{purchase_order.po_number}' can no longer be edited (status: {purchase_order.status})"
            )

        if data.notes is not None:
            purchase_order.notes = data.notes
        if data.expected_delivery_date is not None:
            purchase_order.expected_delivery_date = data.expected_delivery_date

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="purchase_order.updated",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            diff={"notes": purchase_order.notes, "expected_delivery_date": purchase_order.expected_delivery_date},
        )
        self.db.flush()
        return purchase_order


class UpdatePurchaseOrderStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.purchase_orders = PurchaseOrderRepository(db)

    def execute(self, data: UpdatePurchaseOrderStatusInput) -> PurchaseOrder:
        purchase_order = self.purchase_orders.get(company_id=data.company_id, purchase_order_id=data.purchase_order_id)
        if purchase_order is None:
            raise NotFoundError("Purchase order not found")

        if not is_valid_purchase_order_transition(current=purchase_order.status, target=data.status):
            raise InvalidPurchaseOrderTransitionError(
                f"Cannot move purchase order from '{purchase_order.status}' to '{data.status}'"
            )

        old_status = purchase_order.status
        purchase_order.status = data.status
        if data.status == PO_STATUS_CANCELLED:
            purchase_order.cancelled_at = _now()
            if data.cancelled_reason is not None:
                purchase_order.cancelled_reason = data.cancelled_reason

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="purchase_order.status_changed",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            diff={"status": {"old": old_status, "new": purchase_order.status}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=purchasing_events.PURCHASE_ORDER_STATUS_CHANGED,
                company_id=data.company_id,
                payload={
                    "purchase_order_id": str(purchase_order.id),
                    "old_status": old_status,
                    "new_status": purchase_order.status,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return purchase_order


class ReceivePurchaseOrderLineUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.purchase_orders = PurchaseOrderRepository(db)
        self.lines = PurchaseOrderLineRepository(db)
        self.receipts = GoodsReceiptRepository(db)
        self.materials = MaterialRepository(db)

    def execute(self, data: ReceivePurchaseOrderLineInput) -> GoodsReceipt:
        purchase_order = self.purchase_orders.get(company_id=data.company_id, purchase_order_id=data.purchase_order_id)
        if purchase_order is None:
            raise NotFoundError("Purchase order not found")
        if purchase_order.status not in PURCHASE_ORDER_STATUSES_RECEIVABLE:
            raise PurchaseOrderNotReceivableError(
                f"Purchase order '{purchase_order.po_number}' is not receivable (status: {purchase_order.status})"
            )

        line = self.lines.get(company_id=data.company_id, line_id=data.line_id)
        if line is None or line.purchase_order_id != purchase_order.id:
            raise NotFoundError("Purchase order line not found")

        if data.quantity_received <= 0:
            raise InvalidReceiptQuantityError("Received quantity must be greater than zero")
        remaining = Decimal(line.quantity) - Decimal(line.quantity_received)
        if data.quantity_received > remaining:
            raise InvalidReceiptQuantityError(
                f"Cannot receive {data.quantity_received} {line.unit} -- only {remaining} {line.unit} remain on this line"
            )

        slab_id = None
        wants_slab = data.warehouse_id is not None and data.slab_number is not None
        if wants_slab:
            if line.material_id is None:
                raise ReceivedLineHasNoMaterialError(
                    "This line has no linked catalog material -- cannot create a slab from it"
                )
            slab = CreateSlabUseCase(self.db).execute(
                CreateSlabInput(
                    company_id=data.company_id,
                    actor_user_id=data.actor_user_id,
                    material_id=uuid.UUID(str(line.material_id)),
                    warehouse_id=data.warehouse_id,
                    slab_number=data.slab_number,
                    length_mm=data.length_mm,
                    width_mm=data.width_mm,
                )
            )
            slab_id = slab.id

        line.quantity_received = Decimal(line.quantity_received) + data.quantity_received

        receipt = GoodsReceipt(
            company_id=data.company_id,
            purchase_order_id=purchase_order.id,
            purchase_order_line_id=line.id,
            slab_id=slab_id,
            quantity_received=data.quantity_received,
            notes=data.notes,
            received_by=data.actor_user_id,
            received_at=_now(),
        )
        self.receipts.add(receipt)

        # Recompute the order's overall status from every line's own
        # received-vs-ordered quantity -- never set manually, so it can
        # never drift from what was actually received (same discipline as
        # Finance's invoice partially_paid/paid).
        all_lines = self.lines.list_for_order(company_id=data.company_id, purchase_order_id=purchase_order.id)
        fully_received = all(Decimal(l.quantity_received) >= Decimal(l.quantity) for l in all_lines)
        any_received = any(Decimal(l.quantity_received) > 0 for l in all_lines)
        old_status = purchase_order.status
        if fully_received:
            purchase_order.status = PO_STATUS_RECEIVED
        elif any_received:
            purchase_order.status = PO_STATUS_PARTIALLY_RECEIVED

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="purchase_order.line_received",
            entity_type="purchase_order_line",
            entity_id=line.id,
            diff={"quantity_received": str(data.quantity_received), "slab_id": str(slab_id) if slab_id else None},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=purchasing_events.PURCHASE_ORDER_LINE_RECEIVED,
                company_id=data.company_id,
                payload={
                    "purchase_order_id": str(purchase_order.id),
                    "line_id": str(line.id),
                    "quantity_received": str(data.quantity_received),
                    "slab_id": str(slab_id) if slab_id else None,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        if purchase_order.status != old_status:
            event_bus.publish(
                Event(
                    name=purchasing_events.PURCHASE_ORDER_STATUS_CHANGED,
                    company_id=data.company_id,
                    payload={
                        "purchase_order_id": str(purchase_order.id),
                        "old_status": old_status,
                        "new_status": purchase_order.status,
                    },
                    published_by_module=MODULE,
                ),
                self.db,
            )
        return receipt
