"""Task use cases: full CRUD, status transitions (spawning the next
occurrence of a recurring task on completion), and deletion.

Operates directly on the SQLAlchemy model rather than through a pure domain
entity + repository-mapping layer -- CRM's original Phase 2 shape (see
domain/entities.py) was simplified starting with the Catalog module, and
every module built since (6 of 7) follows that simpler shape. Tasks follows
the later, dominant convention rather than resurrecting the original one.
"""
import calendar
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.auth.models import UserCompanyRole
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.crm.application.dtos import (
    CreateTaskInput,
    DeleteTaskInput,
    UpdateTaskInput,
    UpdateTaskStatusInput,
)
from modules.crm.domain import events as crm_events
from modules.crm.domain.exceptions import (
    InvalidRecurrenceError,
    InvalidTaskTransitionError,
    TaskImmutableError,
)
from modules.crm.domain.value_objects import (
    DEFAULT_TASK_PRIORITY,
    DEFAULT_TASK_STATUS,
    NOTIFICATION_TYPE_TASK_ASSIGNED,
    NOTIFICATION_TYPE_TASK_REASSIGNED,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_DONE,
    TERMINAL_TASK_STATUSES,
    is_valid_task_transition,
)
from modules.crm.infrastructure.models.task import Task
from modules.crm.infrastructure.models.task_notification import TaskNotification
from modules.crm.infrastructure.repositories.task_notification_repository import TaskNotificationRepository
from modules.crm.infrastructure.repositories.task_repository import TaskRepository

MODULE_NAME = "crm"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_user_belongs_to_company(db: Session, *, company_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Guards against assigning a task to a UUID that doesn't correspond to
    an actual member of the active company -- same rationale as Customer's
    _ensure_manager_belongs_to_company."""
    exists = db.scalar(
        select(UserCompanyRole.id).where(
            UserCompanyRole.company_id == company_id, UserCompanyRole.user_id == user_id
        )
    )
    if exists is None:
        raise ValidationAPIError(
            "assigned_to does not refer to a member of this company",
            details=[{"field": "assigned_to", "issue": "no such user in this company"}],
        )


def _add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _next_due_date(current_due: datetime, *, rule: str, interval: int) -> datetime:
    if rule == "daily":
        return current_due + timedelta(days=interval)
    if rule == "weekly":
        return current_due + timedelta(weeks=interval)
    if rule == "monthly":
        return _add_months(current_due, interval)
    if rule == "yearly":
        return _add_months(current_due, interval * 12)
    raise InvalidRecurrenceError(f"Unknown recurrence rule '{rule}'")


def _notify(
    db: Session,
    *,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    message: str,
    task_id: uuid.UUID,
) -> None:
    db.add(TaskNotification(
        company_id=company_id,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        task_id=task_id,
    ))
    db.flush()


class CreateTaskUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)

    def execute(self, data: CreateTaskInput) -> Task:
        if data.assigned_to is not None:
            _ensure_user_belongs_to_company(self.db, company_id=data.company_id, user_id=data.assigned_to)

        if data.is_recurring and (data.due_date is None or not data.recurrence_rule):
            raise InvalidRecurrenceError("A recurring task needs both a due date and a recurrence rule")

        task = Task(
            company_id=data.company_id,
            title=data.title,
            description=data.description,
            priority=data.priority or DEFAULT_TASK_PRIORITY,
            status=DEFAULT_TASK_STATUS,
            tags=data.tags,
            due_date=data.due_date,
            remind_at=data.remind_at,
            assigned_to=data.assigned_to,
            related_entity_type=data.related_entity_type,
            related_entity_id=data.related_entity_id,
            is_recurring=data.is_recurring,
            recurrence_rule=data.recurrence_rule if data.is_recurring else None,
            recurrence_interval=data.recurrence_interval or 1,
            recurrence_end_date=data.recurrence_end_date if data.is_recurring else None,
            created_by=data.actor_user_id,
        )
        self.tasks.add(task)

        if task.assigned_to is not None and task.assigned_to != data.actor_user_id:
            _notify(
                self.db,
                company_id=data.company_id,
                user_id=task.assigned_to,
                notification_type=NOTIFICATION_TYPE_TASK_ASSIGNED,
                title="New task assigned",
                message=f'You were assigned: "{task.title}"',
                task_id=task.id,
            )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="task.created",
            entity_type="task",
            entity_id=task.id,
            diff={"title": task.title, "assigned_to": str(task.assigned_to) if task.assigned_to else None},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=crm_events.TASK_CREATED,
                company_id=data.company_id,
                payload={"task_id": str(task.id), "title": task.title},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return task


class UpdateTaskUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)

    def execute(self, data: UpdateTaskInput) -> Task:
        task = self.tasks.get(company_id=data.company_id, task_id=data.task_id)
        if task is None:
            raise NotFoundError("Task not found")
        if task.status in TERMINAL_TASK_STATUSES:
            raise TaskImmutableError(f"Cannot edit a {task.status} task")

        diff = {}
        if data.title is not None and data.title != task.title:
            diff["title"] = {"old": task.title, "new": data.title}
            task.title = data.title
        if data.description is not None and data.description != task.description:
            diff["description"] = {"old": task.description, "new": data.description}
            task.description = data.description
        if data.priority is not None and data.priority != task.priority:
            diff["priority"] = {"old": task.priority, "new": data.priority}
            task.priority = data.priority
        if data.due_date is not None and data.due_date != task.due_date:
            diff["due_date"] = {"old": str(task.due_date), "new": str(data.due_date)}
            task.due_date = data.due_date
        if data.remind_at is not None and data.remind_at != task.remind_at:
            diff["remind_at"] = {"old": str(task.remind_at), "new": str(data.remind_at)}
            task.remind_at = data.remind_at
            task.reminder_sent_at = None
        if data.tags is not None and data.tags != list(task.tags or []):
            diff["tags"] = {"old": task.tags, "new": data.tags}
            task.tags = data.tags
        if data.related_entity_type is not None and data.related_entity_type != task.related_entity_type:
            diff["related_entity_type"] = {"old": task.related_entity_type, "new": data.related_entity_type}
            task.related_entity_type = data.related_entity_type
        if data.related_entity_id is not None and data.related_entity_id != task.related_entity_id:
            diff["related_entity_id"] = {"old": str(task.related_entity_id), "new": str(data.related_entity_id)}
            task.related_entity_id = data.related_entity_id
        if data.is_recurring is not None and data.is_recurring != task.is_recurring:
            diff["is_recurring"] = {"old": task.is_recurring, "new": data.is_recurring}
            task.is_recurring = data.is_recurring
        if data.recurrence_rule is not None and data.recurrence_rule != task.recurrence_rule:
            diff["recurrence_rule"] = {"old": task.recurrence_rule, "new": data.recurrence_rule}
            task.recurrence_rule = data.recurrence_rule
        if data.recurrence_interval is not None and data.recurrence_interval != task.recurrence_interval:
            diff["recurrence_interval"] = {"old": task.recurrence_interval, "new": data.recurrence_interval}
            task.recurrence_interval = data.recurrence_interval
        if data.recurrence_end_date is not None and data.recurrence_end_date != task.recurrence_end_date:
            diff["recurrence_end_date"] = {"old": task.recurrence_end_date, "new": data.recurrence_end_date}
            task.recurrence_end_date = data.recurrence_end_date

        if task.is_recurring and (task.due_date is None or not task.recurrence_rule):
            raise InvalidRecurrenceError("A recurring task needs both a due date and a recurrence rule")

        reassigned = False
        if data.assigned_to is not None and data.assigned_to != task.assigned_to:
            _ensure_user_belongs_to_company(self.db, company_id=data.company_id, user_id=data.assigned_to)
            diff["assigned_to"] = {
                "old": str(task.assigned_to) if task.assigned_to else None,
                "new": str(data.assigned_to),
            }
            task.assigned_to = data.assigned_to
            reassigned = True

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="task.updated",
            entity_type="task",
            entity_id=task.id,
            diff=diff,
        )
        self.db.flush()

        if reassigned and task.assigned_to != data.actor_user_id:
            _notify(
                self.db,
                company_id=data.company_id,
                user_id=task.assigned_to,
                notification_type=NOTIFICATION_TYPE_TASK_REASSIGNED,
                title="Task reassigned to you",
                message=f'You were assigned: "{task.title}"',
                task_id=task.id,
            )

        event_bus.publish(
            Event(
                name=crm_events.TASK_UPDATED,
                company_id=data.company_id,
                payload={"task_id": str(task.id), "diff": diff},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return task


class UpdateTaskStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)

    def execute(self, data: UpdateTaskStatusInput) -> Task:
        task = self.tasks.get(company_id=data.company_id, task_id=data.task_id)
        if task is None:
            raise NotFoundError("Task not found")
        if not is_valid_task_transition(current=task.status, target=data.status):
            raise InvalidTaskTransitionError(f"Cannot move task from '{task.status}' to '{data.status}'")

        old_status = task.status
        task.status = data.status
        now = _now()

        if data.status == TASK_STATUS_DONE:
            task.completed_at = now
            if task.is_recurring:
                self._spawn_next_occurrence(task)
        elif data.status == TASK_STATUS_CANCELLED:
            task.cancelled_at = now
            task.cancelled_reason = data.cancelled_reason

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="task.status_changed",
            entity_type="task",
            entity_id=task.id,
            diff={"status": {"old": old_status, "new": task.status}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=crm_events.TASK_STATUS_CHANGED,
                company_id=data.company_id,
                payload={"task_id": str(task.id), "old_status": old_status, "new_status": task.status},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        if data.status == TASK_STATUS_DONE:
            event_bus.publish(
                Event(
                    name=crm_events.TASK_COMPLETED,
                    company_id=data.company_id,
                    payload={"task_id": str(task.id)},
                    published_by_module=MODULE_NAME,
                ),
                self.db,
            )
        elif data.status == TASK_STATUS_CANCELLED:
            event_bus.publish(
                Event(
                    name=crm_events.TASK_CANCELLED,
                    company_id=data.company_id,
                    payload={"task_id": str(task.id), "reason": data.cancelled_reason},
                    published_by_module=MODULE_NAME,
                ),
                self.db,
            )

        return task

    def _spawn_next_occurrence(self, task: Task) -> None:
        next_due = _next_due_date(task.due_date, rule=task.recurrence_rule, interval=task.recurrence_interval)

        if task.recurrence_end_date:
            # Compared as dates, not datetimes -- SQLite round-trips
            # DateTime columns as naive (drops tzinfo), so comparing
            # timezone-aware datetimes here would raise for any task that
            # was re-fetched from the DB rather than just constructed.
            end_date = datetime.strptime(task.recurrence_end_date, "%Y-%m-%d").date()
            if next_due.date() > end_date:
                return

        series_id = task.series_id or task.id
        next_remind_at = None
        if task.remind_at is not None:
            # Preserve the same lead time before the due date (e.g. "1 day
            # before") rather than the same absolute reminder moment.
            lead = task.due_date - task.remind_at
            next_remind_at = next_due - lead

        next_task = Task(
            company_id=task.company_id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=DEFAULT_TASK_STATUS,
            tags=list(task.tags or []),
            due_date=next_due,
            remind_at=next_remind_at,
            assigned_to=task.assigned_to,
            related_entity_type=task.related_entity_type,
            related_entity_id=task.related_entity_id,
            is_recurring=True,
            recurrence_rule=task.recurrence_rule,
            recurrence_interval=task.recurrence_interval,
            recurrence_end_date=task.recurrence_end_date,
            series_id=series_id,
            created_by=task.created_by,
        )
        self.tasks.add(next_task)


class DeleteTaskUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)
        self.notifications = TaskNotificationRepository(db)

    def execute(self, data: DeleteTaskInput) -> None:
        task = self.tasks.get(company_id=data.company_id, task_id=data.task_id)
        if task is None:
            raise NotFoundError("Task not found")

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="task.deleted",
            entity_type="task",
            entity_id=task.id,
            diff={"title": task.title},
        )

        event_bus.publish(
            Event(
                name=crm_events.TASK_DELETED,
                company_id=data.company_id,
                payload={"task_id": str(task.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )

        self.notifications.delete_for_task(company_id=data.company_id, task_id=task.id)
        self.tasks.detach_series(company_id=data.company_id, series_root_id=task.id)
        self.tasks.delete(task)
