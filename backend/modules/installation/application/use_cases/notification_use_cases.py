from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from modules.installation.application.dtos import MarkNotificationReadInput
from modules.installation.infrastructure.models.notification import Notification
from modules.installation.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)


class MarkNotificationReadUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.notifications = NotificationRepository(db)

    def execute(self, data: MarkNotificationReadInput) -> Notification:
        notification = self.notifications.get(
            company_id=data.company_id, notification_id=data.notification_id
        )
        if notification is None or notification.user_id != data.actor_user_id:
            raise NotFoundError("Notification not found")

        if notification.read_at is None:
            notification.read_at = datetime.now(timezone.utc)
            self.db.flush()
        return notification
