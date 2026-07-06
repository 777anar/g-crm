"""Reminder/overdue notification generation and read-state management.

There is no background job scheduler wired into any module in this codebase
(Celery/Redis are provisioned per the stack but no worker actually runs
anywhere yet -- see Installation's notification_helper.py for the same
honest constraint). GenerateDueTaskNotificationsUseCase is therefore a
pull, not a push: the frontend calls it once when the Dashboard or Tasks
list loads, and it does real, idempotent work at that moment -- scanning
the caller's own tasks for reminders/due-dates that have newly passed and
creating a notification for each, exactly once per task (guarded by
reminder_sent_at/overdue_notified_at).
"""
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from modules.crm.application.dtos import GenerateDueTaskNotificationsInput, MarkTaskNotificationReadInput
from modules.crm.domain.value_objects import NOTIFICATION_TYPE_TASK_OVERDUE, NOTIFICATION_TYPE_TASK_REMINDER
from modules.crm.infrastructure.models.task_notification import TaskNotification
from modules.crm.infrastructure.repositories.task_notification_repository import TaskNotificationRepository
from modules.crm.infrastructure.repositories.task_repository import TaskRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GenerateDueTaskNotificationsUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)
        self.notifications = TaskNotificationRepository(db)

    def execute(self, data: GenerateDueTaskNotificationsInput) -> List[TaskNotification]:
        now = _now()
        created: List[TaskNotification] = []

        for task in self.tasks.list_due_for_reminder(
            company_id=data.company_id, assigned_to=data.actor_user_id, now=now
        ):
            task.reminder_sent_at = now
            created.append(
                self.notifications.add(
                    TaskNotification(
                        company_id=data.company_id,
                        user_id=data.actor_user_id,
                        notification_type=NOTIFICATION_TYPE_TASK_REMINDER,
                        title="Task reminder",
                        message=f'Reminder: "{task.title}"',
                        task_id=task.id,
                    )
                )
            )

        for task in self.tasks.list_overdue(company_id=data.company_id, assigned_to=data.actor_user_id, now=now):
            task.overdue_notified_at = now
            created.append(
                self.notifications.add(
                    TaskNotification(
                        company_id=data.company_id,
                        user_id=data.actor_user_id,
                        notification_type=NOTIFICATION_TYPE_TASK_OVERDUE,
                        title="Task overdue",
                        message=f'Overdue: "{task.title}"',
                        task_id=task.id,
                    )
                )
            )

        self.db.flush()
        return created


class MarkTaskNotificationReadUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.notifications = TaskNotificationRepository(db)

    def execute(self, data: MarkTaskNotificationReadInput) -> TaskNotification:
        notification = self.notifications.get(company_id=data.company_id, notification_id=data.notification_id)
        if notification is None or notification.user_id != data.actor_user_id:
            raise NotFoundError("Notification not found")

        if notification.read_at is None:
            notification.read_at = _now()
            self.db.flush()
        return notification
