import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.communication.application.dtos import CreateMessageTemplateInput, UpdateMessageTemplateInput
from modules.communication.application.use_cases import (
    CreateMessageTemplateUseCase,
    UpdateMessageTemplateUseCase,
)
from modules.communication.infrastructure.repositories.message_template_repository import (
    MessageTemplateRepository,
)
from modules.communication.presentation.schemas.message_template import (
    MessageTemplateCreate,
    MessageTemplateListOut,
    MessageTemplateOut,
    MessageTemplateUpdate,
)

router = APIRouter()


@router.get("/templates", response_model=MessageTemplateListOut)
def list_templates(
    channel_type: Optional[str] = Query(default=None),
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:templates:read")),
) -> MessageTemplateListOut:
    templates = MessageTemplateRepository(db).list(
        company_id=current_user.active_company_id, channel_type=channel_type, include_inactive=include_inactive
    )
    return MessageTemplateListOut(items=[MessageTemplateOut.model_validate(t) for t in templates])


@router.post("/templates", response_model=MessageTemplateOut)
def create_template(
    payload: MessageTemplateCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:templates:write")),
) -> MessageTemplateOut:
    template = CreateMessageTemplateUseCase(db).execute(
        CreateMessageTemplateInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            body=payload.body,
            channel_type=payload.channel_type,
            shortcut=payload.shortcut,
        )
    )
    db.commit()
    db.refresh(template)
    return MessageTemplateOut.model_validate(template)


@router.get("/templates/{template_id}", response_model=MessageTemplateOut)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:templates:read")),
) -> MessageTemplateOut:
    template = MessageTemplateRepository(db).get(
        company_id=current_user.active_company_id, template_id=template_id
    )
    if template is None:
        raise NotFoundError("Message template not found")
    return MessageTemplateOut.model_validate(template)


@router.patch("/templates/{template_id}", response_model=MessageTemplateOut)
def update_template(
    template_id: uuid.UUID,
    payload: MessageTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:templates:write")),
) -> MessageTemplateOut:
    template = UpdateMessageTemplateUseCase(db).execute(
        UpdateMessageTemplateInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            template_id=template_id,
            name=payload.name,
            body=payload.body,
            channel_type=payload.channel_type,
            shortcut=payload.shortcut,
            is_active=payload.is_active,
        )
    )
    db.commit()
    db.refresh(template)
    return MessageTemplateOut.model_validate(template)
