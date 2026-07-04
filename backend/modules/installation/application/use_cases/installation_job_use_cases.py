"""Installation Job use cases: create from an Order that has reached ready/
delivered, edit its schedule (crew/date/time/route), and change its status --
cascading to the linked Order exactly like Production's WorkOrder does
(reusing Orders' own use case rather than re-deriving its audit/event
handling), plus in-app notifications to the assigned crew.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.installation.application.dtos import (
    CreateInstallationJobInput,
    UpdateInstallationJobInput,
    UpdateInstallationJobStatusInput,
)
from modules.installation.application.notification_helper import notify_crew
from modules.installation.domain import events as installation_events
from modules.installation.domain.exceptions import (
    CrewInactiveError,
    InvalidJobTransitionError,
    JobAlreadyExistsError,
    OrderNotReadyForInstallationError,
)
from modules.installation.domain.value_objects import (
    CREW_STATUS_ACTIVE,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_IN_PROGRESS,
    JOB_STATUS_SCHEDULED,
    NOTIFICATION_TYPE_JOB_ASSIGNED,
    NOTIFICATION_TYPE_JOB_RESCHEDULED,
    NOTIFICATION_TYPE_JOB_STATUS_CHANGED,
    is_valid_job_transition,
)
from modules.installation.infrastructure.models.installation_job import InstallationJob
from modules.installation.infrastructure.repositories.crew_repository import CrewRepository
from modules.installation.infrastructure.repositories.installation_job_repository import (
    InstallationJobRepository,
)
from modules.orders.application.dtos import UpdateOrderItemInput, UpdateOrderStatusInput
from modules.orders.application.use_cases import UpdateOrderItemUseCase, UpdateOrderStatusUseCase
from modules.orders.domain.value_objects import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_INSTALLED,
    ORDER_STATUS_READY,
)
from modules.orders.infrastructure.repositories.order_item_repository import OrderItemRepository
from modules.orders.infrastructure.repositories.order_repository import OrderRepository

MODULE = "installation"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreateInstallationJobUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.jobs = InstallationJobRepository(db)
        self.orders = OrderRepository(db)

    def execute(self, data: CreateInstallationJobInput) -> InstallationJob:
        order = self.orders.get(company_id=data.company_id, order_id=data.order_id)
        if order is None:
            raise NotFoundError("Order not found")

        if order.status not in (ORDER_STATUS_READY, ORDER_STATUS_DELIVERED):
            raise OrderNotReadyForInstallationError(
                f"Order must be '{ORDER_STATUS_READY}' or '{ORDER_STATUS_DELIVERED}' to schedule installation "
                f"(current status: '{order.status}')"
            )

        if self.jobs.get_for_order(company_id=data.company_id, order_id=data.order_id) is not None:
            raise JobAlreadyExistsError("This order already has an installation job")

        year = _now().year
        job_number = self.jobs.next_job_number(company_id=data.company_id, year=year)
        job = InstallationJob(
            company_id=data.company_id,
            order_id=order.id,
            job_number=job_number,
            status=JOB_STATUS_SCHEDULED,
            created_by=data.actor_user_id,
        )
        self.jobs.add(job)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="installation_job.created",
            entity_type="installation_job",
            entity_id=job.id,
            diff={"job_number": job_number, "order_id": str(order.id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=installation_events.JOB_CREATED,
                company_id=data.company_id,
                payload={"job_id": str(job.id), "job_number": job_number, "order_id": str(order.id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return job


class UpdateInstallationJobUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.jobs = InstallationJobRepository(db)
        self.crews = CrewRepository(db)

    def execute(self, data: UpdateInstallationJobInput) -> InstallationJob:
        job = self.jobs.get(company_id=data.company_id, job_id=data.job_id)
        if job is None:
            raise NotFoundError("Installation job not found")

        old_crew_id = job.crew_id
        old_scheduled_date = job.scheduled_date

        if data.crew_id is not None:
            crew = self.crews.get(company_id=data.company_id, crew_id=data.crew_id)
            if crew is None:
                raise NotFoundError("Crew not found")
            if crew.status != CREW_STATUS_ACTIVE:
                raise CrewInactiveError(f"Crew '{crew.name}' is not active")
            job.crew_id = data.crew_id
        if data.scheduled_date is not None:
            job.scheduled_date = data.scheduled_date
        if data.scheduled_time_slot is not None:
            job.scheduled_time_slot = data.scheduled_time_slot
        if data.route_sequence is not None:
            job.route_sequence = data.route_sequence
        if data.notes is not None:
            job.notes = data.notes

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="installation_job.updated",
            entity_type="installation_job",
            entity_id=job.id,
            diff={},
        )

        self._notify_schedule_change(data, job, old_crew_id=old_crew_id, old_scheduled_date=old_scheduled_date)
        return job

    def _notify_schedule_change(
        self,
        data: UpdateInstallationJobInput,
        job: InstallationJob,
        *,
        old_crew_id: Optional[uuid.UUID],
        old_scheduled_date: Optional[str],
    ) -> None:
        if job.crew_id is None:
            return
        if old_crew_id != job.crew_id:
            notify_crew(
                self.db,
                company_id=data.company_id,
                crew_id=job.crew_id,
                notification_type=NOTIFICATION_TYPE_JOB_ASSIGNED,
                title=f"New job assigned: {job.job_number}",
                message=f"You've been assigned to installation job {job.job_number}"
                + (f", scheduled {job.scheduled_date}." if job.scheduled_date else "."),
                installation_job_id=job.id,
            )
        elif old_scheduled_date != job.scheduled_date:
            notify_crew(
                self.db,
                company_id=data.company_id,
                crew_id=job.crew_id,
                notification_type=NOTIFICATION_TYPE_JOB_RESCHEDULED,
                title=f"Job rescheduled: {job.job_number}",
                message=f"Installation job {job.job_number} is now scheduled for {job.scheduled_date}.",
                installation_job_id=job.id,
            )


class UpdateInstallationJobStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.jobs = InstallationJobRepository(db)
        self.order_items = OrderItemRepository(db)

    def execute(self, data: UpdateInstallationJobStatusInput) -> InstallationJob:
        job = self.jobs.get(company_id=data.company_id, job_id=data.job_id)
        if job is None:
            raise NotFoundError("Installation job not found")

        if not is_valid_job_transition(current=job.status, target=data.status):
            raise InvalidJobTransitionError(
                f"Cannot move installation job from '{job.status}' to '{data.status}'"
            )

        old_status = job.status
        job.status = data.status
        now = _now()

        if data.status == JOB_STATUS_IN_PROGRESS:
            job.started_at = now
            self._cascade_item_progress(data, job, installation_status=data.status)
        elif data.status == JOB_STATUS_COMPLETED:
            job.completed_at = now
            if data.completion_notes is not None:
                job.completion_notes = data.completion_notes
            self._cascade_item_progress(data, job, installation_status="done")
            UpdateOrderStatusUseCase(self.db).execute(UpdateOrderStatusInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                order_id=job.order_id,
                status=ORDER_STATUS_INSTALLED,
            ))
        elif data.status == JOB_STATUS_CANCELLED:
            job.cancelled_at = now
            if data.cancelled_reason is not None:
                job.cancelled_reason = data.cancelled_reason
        else:
            # e.g. en_route -- still worth reflecting on the Order's items.
            self._cascade_item_progress(data, job, installation_status=data.status)

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="installation_job.status_changed",
            entity_type="installation_job",
            entity_id=job.id,
            diff={"status": {"old": old_status, "new": job.status}},
        )

        event_bus.publish(
            Event(
                name=installation_events.JOB_STATUS_CHANGED,
                company_id=data.company_id,
                payload={"job_id": str(job.id), "old_status": old_status, "new_status": job.status},
                published_by_module=MODULE,
            ),
            self.db,
        )
        if data.status == JOB_STATUS_COMPLETED:
            event_bus.publish(
                Event(
                    name=installation_events.JOB_COMPLETED,
                    company_id=data.company_id,
                    payload={"job_id": str(job.id), "order_id": str(job.order_id)},
                    published_by_module=MODULE,
                ),
                self.db,
            )
        elif data.status == JOB_STATUS_CANCELLED:
            event_bus.publish(
                Event(
                    name=installation_events.JOB_CANCELLED,
                    company_id=data.company_id,
                    payload={"job_id": str(job.id), "reason": data.cancelled_reason},
                    published_by_module=MODULE,
                ),
                self.db,
            )

        if job.crew_id:
            notify_crew(
                self.db,
                company_id=data.company_id,
                crew_id=job.crew_id,
                notification_type=NOTIFICATION_TYPE_JOB_STATUS_CHANGED,
                title=f"Job {job.job_number}: {data.status.replace('_', ' ')}",
                message=f"Installation job {job.job_number} is now '{data.status.replace('_', ' ')}'.",
                installation_job_id=job.id,
            )

        return job

    def _cascade_item_progress(
        self, data: UpdateInstallationJobStatusInput, job: InstallationJob, *, installation_status: str
    ) -> None:
        """Mirrors the job's status onto every item of its Order, the same
        way Production's WorkOrder keeps OrderItem.production_status in
        sync -- so the Order detail screen shows real installation progress."""
        item_use_case = UpdateOrderItemUseCase(self.db)
        for item in self.order_items.list_for_order(company_id=data.company_id, order_id=job.order_id):
            item_use_case.execute(UpdateOrderItemInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                item_id=item.id,
                installation_status=installation_status,
            ))
