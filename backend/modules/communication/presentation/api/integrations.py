import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.communication.application.dtos import (
    ConfigureChannelCredentialInput,
    ProcessMessageQueueInput,
    SyncImapMailboxInput,
    TestChannelConnectionInput,
)
from modules.communication.application.use_cases import (
    ConfigureChannelCredentialUseCase,
    ProcessMessageQueueUseCase,
    RemoveChannelCredentialUseCase,
    SyncImapMailboxUseCase,
    TestChannelConnectionUseCase,
)
from modules.communication.application.use_cases._provider_resolution import decrypt_config
from modules.communication.infrastructure.repositories.channel_credential_repository import (
    ChannelCredentialRepository,
)
from modules.communication.infrastructure.repositories.integration_log_repository import IntegrationLogRepository
from modules.communication.infrastructure.repositories.message_queue_repository import MessageQueueRepository
from modules.communication.presentation.schemas.channel_credential import (
    ChannelCredentialConfigure,
    ChannelCredentialOut,
    mask_config,
)
from modules.communication.presentation.schemas.integration import (
    ImapSyncOut,
    IntegrationLogListOut,
    MessageQueueListOut,
    ProcessQueueOut,
    TestConnectionOut,
)

router = APIRouter()


def _credential_out(credential) -> ChannelCredentialOut:
    return ChannelCredentialOut(
        id=credential.id,
        channel_id=credential.channel_id,
        provider=credential.provider,
        masked_config=mask_config(decrypt_config(credential)),
        has_webhook_secret=bool(credential.webhook_secret_encrypted),
        health_status=credential.health_status,
        last_checked_at=credential.last_checked_at,
        last_error=credential.last_error,
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )


@router.get("/channels/{channel_id}/credential", response_model=ChannelCredentialOut)
def get_channel_credential(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:channels:settings:read")),
) -> ChannelCredentialOut:
    credential = ChannelCredentialRepository(db).get_by_channel(
        company_id=current_user.active_company_id, channel_id=channel_id
    )
    if credential is None:
        raise NotFoundError("No credential configured for this channel")
    return _credential_out(credential)


@router.put("/channels/{channel_id}/credential", response_model=ChannelCredentialOut)
def configure_channel_credential(
    channel_id: uuid.UUID,
    payload: ChannelCredentialConfigure,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:channels:settings:write")),
) -> ChannelCredentialOut:
    credential = ConfigureChannelCredentialUseCase(db).execute(
        ConfigureChannelCredentialInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            channel_id=channel_id,
            provider=payload.provider,
            config=payload.config,
            webhook_secret=payload.webhook_secret,
        )
    )
    db.commit()
    db.refresh(credential)
    return _credential_out(credential)


@router.delete("/channels/{channel_id}/credential")
def remove_channel_credential(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:channels:settings:write")),
) -> dict:
    RemoveChannelCredentialUseCase(db).execute(
        company_id=current_user.active_company_id, actor_user_id=current_user.user_id, channel_id=channel_id
    )
    db.commit()
    return {"ok": True}


@router.post("/channels/{channel_id}/test-connection", response_model=TestConnectionOut)
def test_channel_connection(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:integrations:write")),
) -> TestConnectionOut:
    result = TestChannelConnectionUseCase(db).execute(
        TestChannelConnectionInput(
            company_id=current_user.active_company_id, actor_user_id=current_user.user_id, channel_id=channel_id
        )
    )
    db.commit()
    return TestConnectionOut(**result)


@router.post("/channels/{channel_id}/imap-sync", response_model=ImapSyncOut)
def sync_imap_mailbox(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:integrations:write")),
) -> ImapSyncOut:
    result = SyncImapMailboxUseCase(db).execute(
        SyncImapMailboxInput(
            company_id=current_user.active_company_id, actor_user_id=current_user.user_id, channel_id=channel_id
        )
    )
    db.commit()
    return ImapSyncOut(**result)


@router.get("/queue", response_model=MessageQueueListOut)
def list_message_queue(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:integrations:read")),
) -> MessageQueueListOut:
    entries = MessageQueueRepository(db).list(company_id=current_user.active_company_id, status=status, limit=limit)
    return MessageQueueListOut(items=entries)


@router.post("/queue/process", response_model=ProcessQueueOut)
def process_message_queue(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:integrations:write")),
) -> ProcessQueueOut:
    result = ProcessMessageQueueUseCase(db).execute(
        ProcessMessageQueueInput(
            company_id=current_user.active_company_id, actor_user_id=current_user.user_id, limit=limit
        )
    )
    db.commit()
    return ProcessQueueOut(**result)


@router.get("/integration-logs", response_model=IntegrationLogListOut)
def list_integration_logs(
    channel_id: Optional[uuid.UUID] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    direction: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:integrations:read")),
) -> IntegrationLogListOut:
    entries = IntegrationLogRepository(db).list(
        company_id=current_user.active_company_id, channel_id=channel_id, provider=provider,
        direction=direction, limit=limit,
    )
    return IntegrationLogListOut(items=entries)
