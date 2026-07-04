"""Work Order use cases: create from an approved-for-production Order
(reserving its slabs into production and advancing the Order), and change
status (cascading slab release/sale, item progress, and Order completion).

Reuses Orders' and Catalog's own use cases for every side effect on their
entities (order status, slab status) rather than re-deriving that logic here
-- so audit log entries and domain events for Order/Slab changes stay
attributed to and shaped exactly like every other Order/Slab change, only
Work Order's own state gets Production's audit/event trail.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import UpdateSlabStatusInput
from modules.catalog.application.use_cases import UpdateSlabStatusUseCase
from modules.catalog.domain.value_objects import (
    SLAB_STATUS_AVAILABLE,
    SLAB_STATUS_IN_PRODUCTION,
    SLAB_STATUS_RESERVED,
    SLAB_STATUS_SOLD,
)
from modules.catalog.infrastructure.repositories.slab_repository import SlabRepository
from modules.orders.application.dtos import UpdateOrderItemInput, UpdateOrderStatusInput
from modules.orders.application.use_cases import UpdateOrderItemUseCase, UpdateOrderStatusUseCase
from modules.orders.domain.value_objects import (
    ORDER_STATUS_APPROVED_FOR_PRODUCTION,
    ORDER_STATUS_IN_PRODUCTION,
    ORDER_STATUS_READY,
)
from modules.orders.infrastructure.repositories.order_item_repository import OrderItemRepository
from modules.orders.infrastructure.repositories.order_repository import OrderRepository
from modules.production.application.dtos import CreateWorkOrderInput, UpdateWorkOrderStatusInput
from modules.production.domain import events as production_events
from modules.production.domain.exceptions import (
    InvalidWorkOrderTransitionError,
    NoProductionItemsError,
    OrderNotReadyForProductionError,
    SlabNotReservedError,
    WorkOrderAlreadyExistsError,
)
from modules.production.domain.value_objects import (
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_QUEUED,
    is_valid_work_order_transition,
)
from modules.production.infrastructure.models.work_order import WorkOrder
from modules.production.infrastructure.models.work_order_item import WorkOrderItem
from modules.production.infrastructure.repositories.work_order_item_repository import WorkOrderItemRepository
from modules.production.infrastructure.repositories.work_order_repository import WorkOrderRepository

MODULE = "production"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreateWorkOrderUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.work_orders = WorkOrderRepository(db)
        self.work_order_items = WorkOrderItemRepository(db)
        self.orders = OrderRepository(db)
        self.order_items = OrderItemRepository(db)
        self.slabs = SlabRepository(db)

    def execute(self, data: CreateWorkOrderInput) -> WorkOrder:
        order = self.orders.get(company_id=data.company_id, order_id=data.order_id)
        if order is None:
            raise NotFoundError("Order not found")

        if order.status != ORDER_STATUS_APPROVED_FOR_PRODUCTION:
            raise OrderNotReadyForProductionError(
                f"Order must be '{ORDER_STATUS_APPROVED_FOR_PRODUCTION}' to start a work order "
                f"(current status: '{order.status}')"
            )

        if self.work_orders.get_for_order(company_id=data.company_id, order_id=data.order_id) is not None:
            raise WorkOrderAlreadyExistsError("This order already has a work order")

        items = [
            item
            for item in self.order_items.list_for_order(company_id=data.company_id, order_id=data.order_id)
            if item.slab_id is not None
        ]
        if not items:
            raise NoProductionItemsError("Order has no slab-linked items to send to production")

        for item in items:
            slab = self.slabs.get(company_id=data.company_id, slab_id=item.slab_id)
            if slab is None or slab.status != SLAB_STATUS_RESERVED:
                raise SlabNotReservedError(
                    f"Slab for item '{item.description}' is not reserved "
                    f"(status: {slab.status if slab else 'not found'})"
                )

        year = _now().year
        work_order_number = self.work_orders.next_work_order_number(company_id=data.company_id, year=year)
        work_order = WorkOrder(
            company_id=data.company_id,
            order_id=order.id,
            work_order_number=work_order_number,
            status=WORK_ORDER_STATUS_QUEUED,
            created_by=data.actor_user_id,
        )
        self.work_orders.add(work_order)

        slab_use_case = UpdateSlabStatusUseCase(self.db)
        for item in items:
            self.work_order_items.add(WorkOrderItem(
                company_id=data.company_id,
                work_order_id=work_order.id,
                order_item_id=item.id,
                slab_id=item.slab_id,
            ))
            slab_use_case.execute(UpdateSlabStatusInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                slab_id=item.slab_id,
                status=SLAB_STATUS_IN_PRODUCTION,
            ))

        UpdateOrderStatusUseCase(self.db).execute(UpdateOrderStatusInput(
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            order_id=order.id,
            status=ORDER_STATUS_IN_PRODUCTION,
        ))

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="work_order.created",
            entity_type="work_order",
            entity_id=work_order.id,
            diff={"work_order_number": work_order_number, "order_id": str(order.id), "item_count": len(items)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=production_events.WORK_ORDER_CREATED,
                company_id=data.company_id,
                payload={
                    "work_order_id": str(work_order.id),
                    "work_order_number": work_order_number,
                    "order_id": str(order.id),
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return work_order


class UpdateWorkOrderStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.work_orders = WorkOrderRepository(db)
        self.work_order_items = WorkOrderItemRepository(db)

    def execute(self, data: UpdateWorkOrderStatusInput) -> WorkOrder:
        work_order = self.work_orders.get(company_id=data.company_id, work_order_id=data.work_order_id)
        if work_order is None:
            raise NotFoundError("Work order not found")

        if not is_valid_work_order_transition(current=work_order.status, target=data.status):
            raise InvalidWorkOrderTransitionError(
                f"Cannot move work order from '{work_order.status}' to '{data.status}'"
            )

        old_status = work_order.status
        work_order.status = data.status
        now = _now()

        items = self.work_order_items.list_for_work_order(company_id=data.company_id, work_order_id=work_order.id)

        if data.status == WORK_ORDER_STATUS_COMPLETED:
            work_order.completed_at = now
            self._cascade_slabs(items, data, target_status=SLAB_STATUS_SOLD)
            self._cascade_item_progress(items, data, production_status="done")
            UpdateOrderStatusUseCase(self.db).execute(UpdateOrderStatusInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                order_id=work_order.order_id,
                status=ORDER_STATUS_READY,
            ))
        elif data.status == WORK_ORDER_STATUS_CANCELLED:
            work_order.cancelled_at = now
            if data.cancelled_reason is not None:
                work_order.cancelled_reason = data.cancelled_reason
            self._cascade_slabs(items, data, target_status=SLAB_STATUS_AVAILABLE)
        else:
            # Intermediate shop-floor stages (cutting/polishing/quality_check) --
            # mirror the work order's own status onto each item's production_status
            # so the Order detail screen shows real progress without polling.
            self._cascade_item_progress(items, data, production_status=data.status)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="work_order.status_changed",
            entity_type="work_order",
            entity_id=work_order.id,
            diff={"status": {"old": old_status, "new": work_order.status}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=production_events.WORK_ORDER_STATUS_CHANGED,
                company_id=data.company_id,
                payload={
                    "work_order_id": str(work_order.id),
                    "old_status": old_status,
                    "new_status": work_order.status,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )

        if data.status == WORK_ORDER_STATUS_COMPLETED:
            event_bus.publish(
                Event(
                    name=production_events.WORK_ORDER_COMPLETED,
                    company_id=data.company_id,
                    payload={"work_order_id": str(work_order.id), "order_id": str(work_order.order_id)},
                    published_by_module=MODULE,
                ),
                self.db,
            )
        elif data.status == WORK_ORDER_STATUS_CANCELLED:
            event_bus.publish(
                Event(
                    name=production_events.WORK_ORDER_CANCELLED,
                    company_id=data.company_id,
                    payload={"work_order_id": str(work_order.id), "reason": data.cancelled_reason},
                    published_by_module=MODULE,
                ),
                self.db,
            )

        return work_order

    def _cascade_slabs(self, items, data: UpdateWorkOrderStatusInput, *, target_status: str) -> None:
        slab_use_case = UpdateSlabStatusUseCase(self.db)
        for item in items:
            slab_use_case.execute(UpdateSlabStatusInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                slab_id=item.slab_id,
                status=target_status,
            ))

    def _cascade_item_progress(self, items, data: UpdateWorkOrderStatusInput, *, production_status: str) -> None:
        item_use_case = UpdateOrderItemUseCase(self.db)
        for item in items:
            item_use_case.execute(UpdateOrderItemInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                item_id=item.order_item_id,
                production_status=production_status,
            ))
