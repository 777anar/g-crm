import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.installation.infrastructure.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def get(self, *, company_id: uuid.UUID, notification_id: uuid.UUID) -> Optional[Notification]:
        return self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id, Notification.company_id == company_id
            )
        )

    def list_for_user(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50
    ) -> List[Notification]:
        stmt = select(Notification).where(
            Notification.company_id == company_id, Notification.user_id == user_id
        )
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())
