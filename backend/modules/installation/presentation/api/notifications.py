import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.installation.application.dtos import MarkNotificationReadInput
from modules.installation.application.use_cases import MarkNotificationReadUseCase
from modules.installation.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from modules.installation.presentation.schemas.notification import NotificationListOut, NotificationOut

router = APIRouter()


@router.get("", response_model=NotificationListOut)
def list_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> NotificationListOut:
    notifications = NotificationRepository(db).list_for_user(
        company_id=current_user.active_company_id, user_id=current_user.user_id, unread_only=unread_only
    )
    return NotificationListOut(items=[NotificationOut.model_validate(n) for n in notifications])


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> NotificationOut:
    notification = MarkNotificationReadUseCase(db).execute(
        MarkNotificationReadInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            notification_id=notification_id,
        )
    )
    db.commit()
    return NotificationOut.model_validate(notification)
