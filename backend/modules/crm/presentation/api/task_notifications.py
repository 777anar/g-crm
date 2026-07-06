import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.crm.application.dtos import GenerateDueTaskNotificationsInput, MarkTaskNotificationReadInput
from modules.crm.application.use_cases import GenerateDueTaskNotificationsUseCase, MarkTaskNotificationReadUseCase
from modules.crm.infrastructure.repositories.task_notification_repository import TaskNotificationRepository
from modules.crm.presentation.schemas.task import TaskNotificationListOut, TaskNotificationOut

router = APIRouter()


@router.get("/task-notifications", response_model=TaskNotificationListOut)
def list_task_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:read")),
) -> TaskNotificationListOut:
    notifications = TaskNotificationRepository(db).list_for_user(
        company_id=current_user.active_company_id, user_id=current_user.user_id, unread_only=unread_only
    )
    return TaskNotificationListOut(items=[TaskNotificationOut.model_validate(n) for n in notifications])


@router.post("/task-notifications/check", response_model=TaskNotificationListOut)
def check_task_reminders(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:read")),
) -> TaskNotificationListOut:
    """Generates any newly-due reminder/overdue notifications for the
    calling user's own tasks. Called by the frontend on Dashboard/Tasks
    page load -- see task_notification_use_cases.py for why this is a pull
    rather than a scheduled push."""
    use_case = GenerateDueTaskNotificationsUseCase(db)
    created = use_case.execute(
        GenerateDueTaskNotificationsInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
        )
    )
    db.commit()
    return TaskNotificationListOut(items=[TaskNotificationOut.model_validate(n) for n in created])


@router.post("/task-notifications/{notification_id}/read", response_model=TaskNotificationOut)
def mark_task_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:read")),
) -> TaskNotificationOut:
    notification = MarkTaskNotificationReadUseCase(db).execute(
        MarkTaskNotificationReadInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            notification_id=notification_id,
        )
    )
    db.commit()
    return TaskNotificationOut.model_validate(notification)
