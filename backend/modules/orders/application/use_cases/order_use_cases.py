"""Order use cases: create from accepted quote, update mutable fields, change status."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import CreateSlabReservationInput
from modules.catalog.application.use_cases import CreateSlabReservationUseCase
from modules.orders.application.dtos import (
    CreateOrderInput,
    UpdateOrderInput,
    UpdateOrderItemInput,
    UpdateOrderStatusInput,
)
from modules.orders.domain import events as order_events
from modules.orders.domain.exceptions import (
    InvalidOrderTransitionError,
    OrderImmutableError,
    QuoteNotAcceptedError,
)
from modules.orders.domain.value_objects import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    TERMINAL_ORDER_STATUSES,
    is_valid_order_transition,
)
from modules.orders.infrastructure.models.order import Order
from modules.orders.infrastructure.models.order_item import OrderItem
from modules.orders.infrastructure.models.order_measurement import OrderMeasurement
from modules.orders.infrastructure.models.order_section import OrderSection
from modules.orders.infrastructure.repositories.order_item_repository import OrderItemRepository
from modules.orders.infrastructure.repositories.order_measurement_repository import OrderMeasurementRepository
from modules.orders.infrastructure.repositories.order_repository import OrderRepository
from modules.orders.infrastructure.repositories.order_section_repository import OrderSectionRepository
from modules.sales.infrastructure.repositories.item_repository import ItemRepository
from modules.sales.infrastructure.repositories.measurement_repository import MeasurementRepository
from modules.sales.infrastructure.repositories.quote_repository import QuoteRepository
from modules.sales.infrastructure.repositories.section_repository import SectionRepository

MODULE = "orders"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreateOrderUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)
        self.order_sections = OrderSectionRepository(db)
        self.order_items = OrderItemRepository(db)
        self.order_measurements = OrderMeasurementRepository(db)
        self.quotes = QuoteRepository(db)
        self.sections = SectionRepository(db)
        self.items = ItemRepository(db)
        self.measurements = MeasurementRepository(db)

    def execute(self, data: CreateOrderInput) -> Order:
        quote = self.quotes.get(company_id=data.company_id, quote_id=data.quote_id)
        if quote is None:
            raise NotFoundError("Quote not found")

        if quote.status != "accepted":
            raise QuoteNotAcceptedError(
                f"Cannot create an order from a quote with status '{quote.status}'. Quote must be accepted."
            )

        year = _now().year
        order_number = self.orders.next_order_number(company_id=data.company_id, year=year)

        order = Order(
            company_id=data.company_id,
            project_id=quote.project_id,
            customer_id=quote.customer_id,
            quote_id=quote.id,
            order_number=order_number,
            currency=quote.currency,
            created_by=data.actor_user_id,
            # Financial snapshot
            subtotal_gross=quote.subtotal_gross,
            discount_type=quote.discount_type,
            discount_value=quote.discount_value,
            discount_amount=quote.discount_amount,
            subtotal_after_discount=quote.subtotal_after_discount,
            vat_rate=quote.vat_rate,
            vat_amount=quote.vat_amount,
            total_final=quote.total_final,
            total_internal_cost=quote.total_internal_cost,
            total_profit=quote.total_profit,
        )
        self.orders.add(order)

        # Deep-copy sections, items, measurements
        orig_sections = self.sections.list_for_quote(
            company_id=data.company_id, quote_id=quote.id
        )
        for orig_sec in orig_sections:
            new_sec = OrderSection(
                company_id=data.company_id,
                order_id=order.id,
                name=orig_sec.name,
                sort_order=orig_sec.sort_order,
                notes=orig_sec.notes,
                total_measured_area=orig_sec.total_measured_area,
                subtotal_sale=orig_sec.subtotal_sale,
                subtotal_cost=orig_sec.subtotal_cost,
            )
            self.db.add(new_sec)
            self.db.flush()

            for orig_item in self.items.list_for_section(
                company_id=data.company_id, section_id=orig_sec.id
            ):
                new_item = OrderItem(
                    company_id=data.company_id,
                    order_id=order.id,
                    section_id=new_sec.id,
                    item_type=orig_item.item_type,
                    sort_order=orig_item.sort_order,
                    description=orig_item.description,
                    material_id=orig_item.material_id,
                    slab_id=orig_item.slab_id,
                    quantity=orig_item.quantity,
                    unit=orig_item.unit,
                    unit_sale_price=orig_item.unit_sale_price,
                    unit_cost_price=orig_item.unit_cost_price,
                    line_total_sale=orig_item.line_total_sale,
                    line_total_cost=orig_item.line_total_cost,
                    notes=orig_item.notes,
                )
                self.db.add(new_item)
                if new_item.slab_id is not None:
                    self.db.flush()
                    self._adopt_reservation(data, order, new_item)

            for orig_m in self.measurements.list_for_section(
                company_id=data.company_id, section_id=orig_sec.id
            ):
                self.db.add(OrderMeasurement(
                    company_id=data.company_id,
                    order_id=order.id,
                    section_id=new_sec.id,
                    sort_order=orig_m.sort_order,
                    label=orig_m.label,
                    length_mm=orig_m.length_mm,
                    width_mm=orig_m.width_mm,
                    thickness_mm=orig_m.thickness_mm,
                    quantity=orig_m.quantity,
                    area_m2=orig_m.area_m2,
                    waste_pct=orig_m.waste_pct,
                    required_area_m2=orig_m.required_area_m2,
                    override_required_area=orig_m.override_required_area,
                    notes=orig_m.notes,
                ))

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="order.created",
            entity_type="order",
            entity_id=order.id,
            diff={"order_number": order_number, "quote_id": str(quote.id)},
        )

        event_bus.publish(
            Event(
                name=order_events.ORDER_CREATED,
                company_id=data.company_id,
                payload={
                    "order_id": str(order.id),
                    "order_number": order_number,
                    "quote_id": str(quote.id),
                    "project_id": str(order.project_id),
                    "customer_id": str(order.customer_id),
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return order

    def _adopt_reservation(self, data: CreateOrderInput, order: Order, order_item: "OrderItem") -> None:
        """Backfills a `SlabReservation` bookkeeping row for an item copied
        from the quote with a slab already attached -- the slab itself was
        already moved to `reserved` at quote-acceptance time (Sales'
        `UpdateQuoteStatusUseCase._reserve_slabs`), so this only records the
        formal reservation, it never re-validates availability."""
        CreateSlabReservationUseCase(self.db).execute(
            CreateSlabReservationInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                slab_id=order_item.slab_id,
                order_id=order.id,
                order_item_id=order_item.id,
                require_available=False,
            )
        )


class UpdateOrderUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)

    def execute(self, data: UpdateOrderInput) -> Order:
        order = self.orders.get(company_id=data.company_id, order_id=data.order_id)
        if order is None:
            raise NotFoundError("Order not found")

        if order.status in TERMINAL_ORDER_STATUSES:
            raise OrderImmutableError(
                f"Order is in terminal status '{order.status}' and cannot be modified."
            )

        if data.notes is not None:
            order.notes = data.notes
        if data.production_notes is not None:
            order.production_notes = data.production_notes
        if data.installation_notes is not None:
            order.installation_notes = data.installation_notes
        if data.delivery_address is not None:
            order.delivery_address = data.delivery_address
        if data.scheduled_production_date is not None:
            order.scheduled_production_date = data.scheduled_production_date
        if data.scheduled_installation_date is not None:
            order.scheduled_installation_date = data.scheduled_installation_date

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="order.updated",
            entity_type="order",
            entity_id=order.id,
            diff={},
        )
        return order


class UpdateOrderStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)

    def execute(self, data: UpdateOrderStatusInput) -> Order:
        order = self.orders.get(company_id=data.company_id, order_id=data.order_id)
        if order is None:
            raise NotFoundError("Order not found")

        if not is_valid_order_transition(current=order.status, target=data.status):
            raise InvalidOrderTransitionError(
                f"Cannot move order from '{order.status}' to '{data.status}'"
            )

        old_status = order.status
        order.status = data.status
        now = _now()

        if data.status == ORDER_STATUS_COMPLETED:
            order.completed_at = now
        elif data.status == ORDER_STATUS_CANCELLED:
            order.cancelled_at = now
            if data.cancelled_reason is not None:
                order.cancelled_reason = data.cancelled_reason

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="order.status_changed",
            entity_type="order",
            entity_id=order.id,
            diff={"status": {"old": old_status, "new": order.status}},
        )

        event_bus.publish(
            Event(
                name=order_events.ORDER_STATUS_CHANGED,
                company_id=data.company_id,
                payload={
                    "order_id": str(order.id),
                    "old_status": old_status,
                    "new_status": order.status,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )

        if data.status == ORDER_STATUS_COMPLETED:
            event_bus.publish(
                Event(
                    name=order_events.ORDER_COMPLETED,
                    company_id=data.company_id,
                    payload={"order_id": str(order.id)},
                    published_by_module=MODULE,
                ),
                self.db,
            )
        elif data.status == ORDER_STATUS_CANCELLED:
            event_bus.publish(
                Event(
                    name=order_events.ORDER_CANCELLED,
                    company_id=data.company_id,
                    payload={"order_id": str(order.id), "reason": data.cancelled_reason},
                    published_by_module=MODULE,
                ),
                self.db,
            )

        return order


class UpdateOrderItemUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)
        self.items = OrderItemRepository(db)

    def execute(self, data: UpdateOrderItemInput) -> "OrderItem":
        item = self.items.get(company_id=data.company_id, item_id=data.item_id)
        if item is None:
            raise NotFoundError("Order item not found")

        if data.production_status is not None:
            item.production_status = data.production_status
        if data.installation_status is not None:
            item.installation_status = data.installation_status
        if data.notes is not None:
            item.notes = data.notes

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="order_item.updated",
            entity_type="order_item",
            entity_id=item.id,
            diff={},
        )
        return item
