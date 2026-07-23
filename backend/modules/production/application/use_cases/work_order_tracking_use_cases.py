"""Work Order tracking use cases (Phase 1: Stone Fabrication Workflow):
priority, assigned operator, due date/notes, and stage progression through
the company's configurable production-stage pipeline. Each mutation
appends a `WorkOrderEvent` row -- the backbone of the production timeline
-- on top of the standard core audit log entry every write already
records."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.auth.models import UserCompanyRole
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.production.application.dtos import (
    AssignWorkOrderOperatorInput,
    UpdateWorkOrderInput,
    UpdateWorkOrderPriorityInput,
    UpdateWorkOrderStageInput,
)
from modules.production.application.notification_helper import notify_user
from modules.production.domain import events as production_events
from modules.production.domain.exceptions import InvalidPriorityError, OperatorNotInCompanyError, StageNotFoundError
from modules.production.domain.value_objects import (
    NOTIFICATION_TYPE_OPERATOR_ASSIGNED,
    NOTIFICATION_TYPE_PRIORITY_URGENT,
    NOTIFICATION_TYPE_STAGE_CHANGED,
    PRIORITY_URGENT,
    VALID_PRIORITIES,
    WORK_ORDER_EVENT_OPERATOR_ASSIGNED,
    WORK_ORDER_EVENT_PRIORITY_CHANGED,
    WORK_ORDER_EVENT_STAGE_CHANGED,
)
from modules.production.infrastructure.models.work_order import WorkOrder
from modules.production.infrastructure.models.work_order_event import WorkOrderEvent
from modules.production.infrastructure.repositories.production_stage_repository import ProductionStageRepository
from modules.production.infrastructure.repositories.work_order_event_repository import WorkOrderEventRepository
from modules.production.infrastructure.repositories.work_order_repository import WorkOrderRepository

MODULE = "production"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_operator_belongs_to_company(db: Session, *, company_id: uuid.UUID, operator_id: uuid.UUID) -> None:
    exists = db.scalar(
        select(UserCompanyRole.id).where(
            UserCompanyRole.company_id == company_id, UserCompanyRole.user_id == operator_id
        )
    )
    if exists is None:
        raise OperatorNotInCompanyError("operator_user_id does not refer to a member of this company")


class UpdateWorkOrderUseCase:
    """Mutable fields on a work order that don't drive any cascade --
    due date and internal notes -- mirroring Orders' own UpdateOrderUseCase
    for the same category of edit."""

    def __init__(self, db: Session):
        self.db = db
        self.work_orders = WorkOrderRepository(db)

    def execute(self, data: UpdateWorkOrderInput) -> WorkOrder:
        work_order = self.work_orders.get(company_id=data.company_id, work_order_id=data.work_order_id)
        if work_order is None:
            raise NotFoundError("Work order not found")

        if data.due_date is not None:
            work_order.scheduled_completion_date = data.due_date
        if data.notes is not None:
            work_order.notes = data.notes

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="work_order.updated",
            entity_type="work_order",
            entity_id=work_order.id,
            diff={},
        )
        return work_order


class UpdateWorkOrderPriorityUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.work_orders = WorkOrderRepository(db)
        self.events = WorkOrderEventRepository(db)

    def execute(self, data: UpdateWorkOrderPriorityInput) -> WorkOrder:
        work_order = self.work_orders.get(company_id=data.company_id, work_order_id=data.work_order_id)
        if work_order is None:
            raise NotFoundError("Work order not found")
        if data.priority not in VALID_PRIORITIES:
            raise InvalidPriorityError(f"priority must be one of {sorted(VALID_PRIORITIES)}")

        old_priority = work_order.priority
        work_order.priority = data.priority
        self.db.flush()

        # Priority/stage-change notifications (Phase 19): only fires when
        # a job is marked `urgent` and there's actually someone assigned to
        # tell -- a priority change on an unassigned job has no one to
        # notify yet (they'll see it once assigned).
        if data.priority == PRIORITY_URGENT and old_priority != PRIORITY_URGENT and work_order.assigned_to:
            notify_user(
                self.db,
                company_id=data.company_id,
                user_id=uuid.UUID(str(work_order.assigned_to)),
                notification_type=NOTIFICATION_TYPE_PRIORITY_URGENT,
                title="Work order marked urgent",
                message=f"Work order {work_order.work_order_number} was marked urgent.",
                work_order_id=work_order.id,
            )

        self.events.add(WorkOrderEvent(
            company_id=data.company_id,
            work_order_id=work_order.id,
            event_type=WORK_ORDER_EVENT_PRIORITY_CHANGED,
            from_value=old_priority,
            to_value=data.priority,
            changed_by=data.actor_user_id,
            changed_at=_now(),
        ))

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="work_order.priority_changed",
            entity_type="work_order",
            entity_id=work_order.id,
            diff={"priority": {"old": old_priority, "new": data.priority}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=production_events.WORK_ORDER_PRIORITY_CHANGED,
                company_id=data.company_id,
                payload={"work_order_id": str(work_order.id), "old_priority": old_priority, "new_priority": data.priority},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return work_order


class AssignWorkOrderOperatorUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.work_orders = WorkOrderRepository(db)
        self.events = WorkOrderEventRepository(db)

    def execute(self, data: AssignWorkOrderOperatorInput) -> WorkOrder:
        work_order = self.work_orders.get(company_id=data.company_id, work_order_id=data.work_order_id)
        if work_order is None:
            raise NotFoundError("Work order not found")

        if data.operator_user_id is not None:
            _ensure_operator_belongs_to_company(
                self.db, company_id=data.company_id, operator_id=data.operator_user_id
            )

        old_operator = str(work_order.assigned_to) if work_order.assigned_to else None
        work_order.assigned_to = data.operator_user_id
        self.db.flush()

        # Notify the newly assigned operator (Phase 19) -- not fired on
        # unassignment (`operator_user_id=None`) or a no-op reassignment to
        # the same person, since neither is news to anyone.
        if data.operator_user_id is not None and str(data.operator_user_id) != old_operator:
            notify_user(
                self.db,
                company_id=data.company_id,
                user_id=data.operator_user_id,
                notification_type=NOTIFICATION_TYPE_OPERATOR_ASSIGNED,
                title="Assigned to a work order",
                message=f"You were assigned to work order {work_order.work_order_number}.",
                work_order_id=work_order.id,
            )

        self.events.add(WorkOrderEvent(
            company_id=data.company_id,
            work_order_id=work_order.id,
            event_type=WORK_ORDER_EVENT_OPERATOR_ASSIGNED,
            from_value=old_operator,
            to_value=str(data.operator_user_id) if data.operator_user_id else None,
            changed_by=data.actor_user_id,
            changed_at=_now(),
        ))

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="work_order.operator_assigned",
            entity_type="work_order",
            entity_id=work_order.id,
            diff={"assigned_to": {"old": old_operator, "new": str(data.operator_user_id) if data.operator_user_id else None}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=production_events.WORK_ORDER_OPERATOR_ASSIGNED,
                company_id=data.company_id,
                payload={"work_order_id": str(work_order.id), "operator_user_id": str(data.operator_user_id) if data.operator_user_id else None},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return work_order


class UpdateWorkOrderStageUseCase:
    """Moves a work order to a different point in the company's
    configurable stage pipeline -- an independent, finer-grained dimension
    from the work order's own coarse status (queued/cutting/.../completed),
    which still drives Order/slab cascades untouched. Stages can be moved
    forward *or* backward (real fabrication shops send pieces back for
    rework), so no transition graph is enforced here beyond "the stage
    must belong to this company and be active"."""

    def __init__(self, db: Session):
        self.db = db
        self.work_orders = WorkOrderRepository(db)
        self.stages = ProductionStageRepository(db)
        self.events = WorkOrderEventRepository(db)

    def execute(self, data: UpdateWorkOrderStageInput) -> WorkOrder:
        work_order = self.work_orders.get(company_id=data.company_id, work_order_id=data.work_order_id)
        if work_order is None:
            raise NotFoundError("Work order not found")

        old_stage = None
        if work_order.current_stage_id is not None:
            old_stage = self.stages.get(company_id=data.company_id, stage_id=uuid.UUID(str(work_order.current_stage_id)))

        new_stage = None
        if data.stage_id is not None:
            new_stage = self.stages.get(company_id=data.company_id, stage_id=data.stage_id)
            if new_stage is None:
                raise StageNotFoundError("stage_id does not refer to a production stage in this company")

        work_order.current_stage_id = data.stage_id
        self.db.flush()

        # Stage-change notification (Phase 19): fires on any real stage
        # move for an assigned job -- deliberately not keyed to a specific
        # stage name like "Quality Control" (the roadmap's example),
        # since stage names are per-company configurable
        # (production_stages.name) and a hardcoded match would silently
        # stop firing the moment a company renames or reorders its pipeline.
        old_stage_id = str(old_stage.id) if old_stage else None
        new_stage_id = str(new_stage.id) if new_stage else None
        if work_order.assigned_to and old_stage_id != new_stage_id:
            notify_user(
                self.db,
                company_id=data.company_id,
                user_id=uuid.UUID(str(work_order.assigned_to)),
                notification_type=NOTIFICATION_TYPE_STAGE_CHANGED,
                title="Work order moved to a new stage",
                message=(
                    f"Work order {work_order.work_order_number} moved to "
                    f"{new_stage.name if new_stage else 'no stage'}."
                ),
                work_order_id=work_order.id,
            )

        self.events.add(WorkOrderEvent(
            company_id=data.company_id,
            work_order_id=work_order.id,
            event_type=WORK_ORDER_EVENT_STAGE_CHANGED,
            from_value=old_stage.name if old_stage else None,
            to_value=new_stage.name if new_stage else None,
            changed_by=data.actor_user_id,
            changed_at=_now(),
        ))

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="work_order.stage_changed",
            entity_type="work_order",
            entity_id=work_order.id,
            diff={"stage": {"old": old_stage.name if old_stage else None, "new": new_stage.name if new_stage else None}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=production_events.WORK_ORDER_STAGE_CHANGED,
                company_id=data.company_id,
                payload={
                    "work_order_id": str(work_order.id),
                    "old_stage_id": str(old_stage.id) if old_stage else None,
                    "new_stage_id": str(new_stage.id) if new_stage else None,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return work_order
