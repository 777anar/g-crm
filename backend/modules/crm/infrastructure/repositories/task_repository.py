import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from modules.crm.domain.value_objects import TERMINAL_TASK_STATUSES
from modules.crm.infrastructure.models.task import Task

# Whitelisted sortable columns -- per API_SPECIFICATION.md's `?sort=field` /
# `?sort=-field` convention, same whitelist-not-getattr rationale as
# CustomerRepository._SORTABLE_COLUMNS.
_SORTABLE_COLUMNS = {
    "title": Task.title,
    "due_date": Task.due_date,
    "priority": Task.priority,
    "status": Task.status,
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
}
DEFAULT_SORT = "-created_at"


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, task: Task) -> Task:
        self.db.add(task)
        self.db.flush()
        return task

    def get(self, *, company_id: uuid.UUID, task_id: uuid.UUID) -> Optional[Task]:
        return self.db.scalar(
            select(Task).where(Task.id == task_id, Task.company_id == company_id)
        )

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.flush()

    def detach_series(self, *, company_id: uuid.UUID, series_root_id: uuid.UUID) -> None:
        """Called before deleting a recurring task's template -- any
        already-generated occurrences stop pointing at it rather than being
        deleted themselves or blocking the delete on the FK."""
        self.db.execute(
            update(Task)
            .where(Task.company_id == company_id, Task.series_id == series_root_id)
            .values(series_id=None)
        )
        self.db.flush()

    def list(
        self,
        *,
        company_id: uuid.UUID,
        assigned_to: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[uuid.UUID] = None,
        due_before: Optional[datetime] = None,
        due_after: Optional[datetime] = None,
        exclude_terminal: bool = False,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Task]:
        stmt = select(Task).where(Task.company_id == company_id)
        if assigned_to:
            stmt = stmt.where(Task.assigned_to == assigned_to)
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if exclude_terminal:
            stmt = stmt.where(Task.status.notin_(TERMINAL_TASK_STATUSES))
        if related_entity_type:
            stmt = stmt.where(Task.related_entity_type == related_entity_type)
        if related_entity_id:
            stmt = stmt.where(Task.related_entity_id == related_entity_id)
        if due_before:
            stmt = stmt.where(Task.due_date.isnot(None), Task.due_date <= due_before)
        if due_after:
            stmt = stmt.where(Task.due_date.isnot(None), Task.due_date >= due_after)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))

        sort = sort or DEFAULT_SORT
        descending = sort.startswith("-")
        column = _SORTABLE_COLUMNS.get(sort.lstrip("-"), Task.created_at)
        stmt = stmt.order_by(column.desc() if descending else column.asc())

        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_for_series(self, *, company_id: uuid.UUID, series_id: uuid.UUID) -> List[Task]:
        stmt = (
            select(Task)
            .where(Task.company_id == company_id, or_(Task.id == series_id, Task.series_id == series_id))
            .order_by(Task.due_date.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_due_for_reminder(self, *, company_id: uuid.UUID, assigned_to: uuid.UUID, now: datetime) -> List[Task]:
        stmt = select(Task).where(
            Task.company_id == company_id,
            Task.assigned_to == assigned_to,
            Task.status.notin_(TERMINAL_TASK_STATUSES),
            Task.remind_at.isnot(None),
            Task.remind_at <= now,
            Task.reminder_sent_at.is_(None),
        )
        return list(self.db.scalars(stmt).all())

    def list_overdue(self, *, company_id: uuid.UUID, assigned_to: uuid.UUID, now: datetime) -> List[Task]:
        stmt = select(Task).where(
            Task.company_id == company_id,
            Task.assigned_to == assigned_to,
            Task.status.notin_(TERMINAL_TASK_STATUSES),
            Task.due_date.isnot(None),
            Task.due_date < now,
            Task.overdue_notified_at.is_(None),
        )
        return list(self.db.scalars(stmt).all())
