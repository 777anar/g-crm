import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.communication.application.dtos import CreateChannelInput, UpdateChannelInput
from modules.communication.application.use_cases import CreateChannelUseCase, UpdateChannelUseCase
from modules.communication.infrastructure.repositories.channel_repository import ChannelRepository
from modules.communication.presentation.schemas.channel import (
    ChannelCreate,
    ChannelListOut,
    ChannelOut,
    ChannelUpdate,
)

router = APIRouter()


@router.get("/channels", response_model=ChannelListOut)
def list_channels(
    channel_type: Optional[str] = Query(default=None),
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:channels:read")),
) -> ChannelListOut:
    channels = ChannelRepository(db).list(
        company_id=current_user.active_company_id, channel_type=channel_type, include_inactive=include_inactive
    )
    return ChannelListOut(items=[ChannelOut.model_validate(c) for c in channels])


@router.post("/channels", response_model=ChannelOut)
def create_channel(
    payload: ChannelCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:channels:write")),
) -> ChannelOut:
    channel = CreateChannelUseCase(db).execute(
        CreateChannelInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            channel_type=payload.channel_type,
            display_name=payload.display_name,
            identifier=payload.identifier,
        )
    )
    db.commit()
    db.refresh(channel)
    return ChannelOut.model_validate(channel)


@router.get("/channels/{channel_id}", response_model=ChannelOut)
def get_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:channels:read")),
) -> ChannelOut:
    channel = ChannelRepository(db).get(company_id=current_user.active_company_id, channel_id=channel_id)
    if channel is None:
        raise NotFoundError("Channel not found")
    return ChannelOut.model_validate(channel)


@router.patch("/channels/{channel_id}", response_model=ChannelOut)
def update_channel(
    channel_id: uuid.UUID,
    payload: ChannelUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:channels:write")),
) -> ChannelOut:
    channel = UpdateChannelUseCase(db).execute(
        UpdateChannelInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            channel_id=channel_id,
            display_name=payload.display_name,
            identifier=payload.identifier,
            is_active=payload.is_active,
        )
    )
    db.commit()
    db.refresh(channel)
    return ChannelOut.model_validate(channel)
