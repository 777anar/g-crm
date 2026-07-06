import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from modules.crm.infrastructure.models.task_notification import TaskNotification


class TaskNotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, notification: TaskNotification) -> TaskNotification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def get(self, *, company_id: uuid.UUID, notification_id: uuid.UUID) -> Optional[TaskNotification]:
        return self.db.scalar(
            select(TaskNotification).where(
                TaskNotification.id == notification_id, TaskNotification.company_id == company_id
            )
        )

    def list_for_user(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50
    ) -> List[TaskNotification]:
        stmt = select(TaskNotification).where(
            TaskNotification.company_id == company_id, TaskNotification.user_id == user_id
        )
        if unread_only:
            stmt = stmt.where(TaskNotification.read_at.is_(None))
        stmt = stmt.order_by(TaskNotification.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def delete_for_task(self, *, company_id: uuid.UUID, task_id: uuid.UUID) -> None:
        """Called before hard-deleting a Task -- there's no DB-level cascade
        configured (this codebase doesn't use ORM relationship() cascades
        anywhere), so the FK-referencing rows must go first."""
        self.db.execute(
            delete(TaskNotification).where(
                TaskNotification.company_id == company_id, TaskNotification.task_id == task_id
            )
        )
        self.db.flush()
