"""Real-integration administration use cases: configuring/removing a
channel's provider credentials, testing a connection, processing the retry
queue, syncing an IMAP mailbox, and recording delivery/read status updates
that arrive from a provider's webhook. Cross-cutting concerns (audit event
+ event bus publish on every write) follow the exact same pattern every
other use case in this module already does.
"""
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.communication.application.dtos import (
    ConfigureChannelCredentialInput,
    ProcessMessageQueueInput,
    SyncImapMailboxInput,
    TestChannelConnectionInput,
    UpdateMessageDeliveryStatusInput,
)
from modules.communication.application.use_cases._provider_resolution import decrypt_config, resolve_provider_and_credential
from modules.communication.domain import events as comm_events
from modules.communication.domain.exceptions import ProviderConfigurationError
from modules.communication.domain.value_objects import (
    HEALTH_STATUS_ERROR,
    HEALTH_STATUS_OK,
    HEALTH_STATUS_UNKNOWN,
    LOG_DIRECTION_OUTBOUND,
    MESSAGE_STATUS_FAILED,
    MESSAGE_STATUS_SENT,
    QUEUE_STATUS_FAILED,
    QUEUE_STATUS_PENDING,
    QUEUE_STATUS_SENT,
    VALID_MESSAGE_STATUSES,
    VALID_PROVIDERS_FOR_CHANNEL_TYPE,
)
from modules.communication.infrastructure.models.channel_credential import ChannelCredential
from modules.communication.infrastructure.models.integration_log_entry import IntegrationLogEntry
from modules.communication.infrastructure.providers.imap_sync_client import ImapMailboxClient
from modules.communication.infrastructure.repositories.channel_credential_repository import (
    ChannelCredentialRepository,
)
from modules.communication.infrastructure.repositories.channel_repository import ChannelRepository
from modules.communication.infrastructure.repositories.conversation_repository import ConversationRepository
from modules.communication.infrastructure.repositories.integration_log_repository import IntegrationLogRepository
from modules.communication.infrastructure.repositories.message_queue_repository import MessageQueueRepository
from modules.communication.infrastructure.repositories.message_repository import MessageRepository
from modules.communication.infrastructure.security.encryption import encrypt_text

MODULE_NAME = "communication"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ConfigureChannelCredentialUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.channels = ChannelRepository(db)
        self.credentials = ChannelCredentialRepository(db)

    def execute(self, data: ConfigureChannelCredentialInput) -> ChannelCredential:
        channel = self.channels.get(company_id=data.company_id, channel_id=data.channel_id)
        if channel is None:
            raise NotFoundError("Channel not found")

        allowed_providers = VALID_PROVIDERS_FOR_CHANNEL_TYPE.get(channel.channel_type, set())
        if data.provider not in allowed_providers:
            raise ValidationAPIError(
                f"Provider '{data.provider}' is not valid for channel_type '{channel.channel_type}'",
                details=[{"field": "provider", "issue": f"must be one of {sorted(allowed_providers)}"}],
            )

        credential = self.credentials.get_by_channel(company_id=data.company_id, channel_id=channel.id)
        is_new = credential is None
        if credential is None:
            credential = ChannelCredential(
                company_id=data.company_id, channel_id=channel.id, provider=data.provider,
                encrypted_config="", created_by=data.actor_user_id,
            )

        credential.provider = data.provider
        credential.encrypted_config = encrypt_text(json.dumps(data.config))
        if data.webhook_secret:
            credential.webhook_secret_encrypted = encrypt_text(data.webhook_secret)
        # Configuration changed -- health is unverified until Test Connection
        # is run again, so we never show a stale "ok" for credentials that
        # may no longer be valid.
        credential.health_status = HEALTH_STATUS_UNKNOWN
        credential.last_error = None

        if is_new:
            self.credentials.add(credential)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="channel.credential_configured",
            entity_type="channel_credential",
            entity_id=credential.id,
            # Never log secret values -- only which fields were set.
            diff={"provider": data.provider, "config_fields": sorted(data.config.keys())},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.CHANNEL_CREDENTIAL_CONFIGURED,
                company_id=data.company_id,
                payload={"channel_id": str(channel.id), "provider": data.provider},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return credential


class RemoveChannelCredentialUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.channels = ChannelRepository(db)
        self.credentials = ChannelCredentialRepository(db)

    def execute(self, *, company_id: uuid.UUID, actor_user_id: uuid.UUID, channel_id: uuid.UUID) -> None:
        channel = self.channels.get(company_id=company_id, channel_id=channel_id)
        if channel is None:
            raise NotFoundError("Channel not found")
        credential = self.credentials.get_by_channel(company_id=company_id, channel_id=channel_id)
        if credential is None:
            raise NotFoundError("No credential configured for this channel")

        self.credentials.delete(credential)
        record_audit(
            self.db,
            company_id=company_id,
            module=MODULE_NAME,
            actor_user_id=actor_user_id,
            action="channel.credential_removed",
            entity_type="channel_credential",
            entity_id=channel_id,
        )
        self.db.flush()


class TestChannelConnectionUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.channels = ChannelRepository(db)
        self.credentials = ChannelCredentialRepository(db)
        self.logs = IntegrationLogRepository(db)

    def execute(self, data: TestChannelConnectionInput) -> Dict[str, Any]:
        channel = self.channels.get(company_id=data.company_id, channel_id=data.channel_id)
        if channel is None:
            raise NotFoundError("Channel not found")

        provider, credential = resolve_provider_and_credential(self.db, channel)
        if credential is None:
            raise NotFoundError("No credential configured for this channel")

        started = time.perf_counter()
        success = False
        detail = ""
        try:
            result = provider.test_connection()
            success = bool(result.get("ok"))
            detail = str(result.get("detail", ""))
        except Exception as exc:  # noqa: BLE001 -- any provider/network failure is a failed health check, not a 500
            detail = str(exc)
        duration_ms = int((time.perf_counter() - started) * 1000)

        credential.health_status = HEALTH_STATUS_OK if success else HEALTH_STATUS_ERROR
        credential.last_checked_at = _now()
        credential.last_error = None if success else detail

        self.logs.add(
            IntegrationLogEntry(
                company_id=data.company_id, channel_id=channel.id, provider=credential.provider,
                direction=LOG_DIRECTION_OUTBOUND, action="test_connection",
                success=success, error_message=None if success else detail, duration_ms=duration_ms,
            )
        )
        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="channel.connection_tested",
            entity_type="channel_credential",
            entity_id=credential.id,
            diff={"health_status": credential.health_status},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.CHANNEL_HEALTH_CHECKED,
                company_id=data.company_id,
                payload={"channel_id": str(channel.id), "health_status": credential.health_status},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return {"ok": success, "detail": detail, "health_status": credential.health_status}


class ProcessMessageQueueUseCase:
    """Re-attempts every due retry-queue entry for this company. Since this
    codebase has no background job scheduler, this is triggered by an
    explicit call (an admin action or the frontend Queue Monitor page),
    exactly like Tasks & Reminders' `POST /crm/task-notifications/check`."""

    def __init__(self, db: Session):
        self.db = db
        self.queue = MessageQueueRepository(db)
        self.messages = MessageRepository(db)
        self.channels = ChannelRepository(db)
        self.conversations = ConversationRepository(db)
        self.logs = IntegrationLogRepository(db)

    def execute(self, data: ProcessMessageQueueInput) -> Dict[str, int]:
        due_entries = self.queue.list_due(company_id=data.company_id, now=_now(), limit=data.limit)
        sent = 0
        failed = 0
        still_pending = 0

        for entry in due_entries:
            message = self.messages.get(company_id=data.company_id, message_id=entry.message_id)
            channel = self.channels.get(company_id=data.company_id, channel_id=entry.channel_id)
            conversation = (
                self.conversations.get(company_id=data.company_id, conversation_id=message.conversation_id)
                if message is not None
                else None
            )
            if message is None or channel is None or conversation is None:
                entry.status = QUEUE_STATUS_FAILED
                entry.last_error = "Message, channel, or conversation no longer exists"
                failed += 1
                continue

            provider, credential = resolve_provider_and_credential(self.db, channel)
            entry.attempts += 1
            started = time.perf_counter()
            success = False
            error_message: Optional[str] = None
            try:
                external_message_id = provider.send(
                    channel=channel,
                    external_contact_id=conversation.external_contact_id,
                    body=message.body or "",
                    message_type=message.message_type,
                )
                message.status = MESSAGE_STATUS_SENT
                message.external_message_id = external_message_id
                entry.status = QUEUE_STATUS_SENT
                success = True
                sent += 1
            except Exception as exc:  # noqa: BLE001 -- classify below by attempts, not exception type
                error_message = str(exc)
                if entry.attempts >= entry.max_attempts:
                    entry.status = QUEUE_STATUS_FAILED
                    message.status = MESSAGE_STATUS_FAILED
                    failed += 1
                else:
                    entry.status = QUEUE_STATUS_PENDING
                    entry.next_attempt_at = _now() + timedelta(minutes=2**entry.attempts)
                    still_pending += 1
                entry.last_error = error_message
            duration_ms = int((time.perf_counter() - started) * 1000)

            self.logs.add(
                IntegrationLogEntry(
                    company_id=data.company_id, channel_id=channel.id,
                    provider=credential.provider if credential else "null",
                    direction=LOG_DIRECTION_OUTBOUND, action="queue_retry",
                    success=success, error_message=error_message, duration_ms=duration_ms,
                )
            )

        self.db.flush()
        return {"processed": len(due_entries), "sent": sent, "failed": failed, "still_pending": still_pending}


class SyncImapMailboxUseCase:
    """Pulls new mail since the last sync -- IMAP has no webhook/push
    mechanism, so this is a pull-triggered action (an admin's "Sync now"
    button), not something that happens automatically."""

    def __init__(self, db: Session):
        self.db = db
        self.channels = ChannelRepository(db)
        self.credentials = ChannelCredentialRepository(db)
        self.logs = IntegrationLogRepository(db)

    def execute(self, data: SyncImapMailboxInput) -> Dict[str, Any]:
        from modules.communication.application.dtos import AddMessageAttachmentInput, ReceiveInboundMessageInput
        from modules.communication.application.use_cases.conversation_use_cases import (
            AddMessageAttachmentUseCase,
            ReceiveInboundMessageUseCase,
        )

        channel = self.channels.get(company_id=data.company_id, channel_id=data.channel_id)
        if channel is None:
            raise NotFoundError("Channel not found")
        credential = self.credentials.get_by_channel(company_id=data.company_id, channel_id=channel.id)
        if credential is None:
            raise NotFoundError("No credential configured for this channel")

        config = decrypt_config(credential)
        if not config.get("imap_host"):
            raise ProviderConfigurationError("This channel's credential has no IMAP configuration")

        client = ImapMailboxClient(config)
        started = time.perf_counter()
        error_message: Optional[str] = None
        synced_count = 0
        try:
            fetched = client.fetch_new_messages(since_uid=credential.imap_last_synced_uid)
            for email_msg in fetched:
                message = ReceiveInboundMessageUseCase(self.db).execute(
                    ReceiveInboundMessageInput(
                        company_id=data.company_id,
                        actor_user_id=data.actor_user_id,
                        channel_id=channel.id,
                        external_contact_id=email_msg.from_address,
                        external_contact_name=email_msg.from_name,
                        body=email_msg.body or email_msg.subject,
                    )
                )
                for attachment in email_msg.attachments:
                    document = _store_email_attachment(
                        company_id=data.company_id, uploaded_by=data.actor_user_id,
                        message_id=message.id, filename=attachment.filename,
                        content=attachment.content, mime_type=attachment.mime_type,
                    )
                    self.db.add(document)
                    self.db.flush()
                    AddMessageAttachmentUseCase(self.db).execute(
                        AddMessageAttachmentInput(
                            company_id=data.company_id, actor_user_id=data.actor_user_id,
                            message_id=message.id, document_id=document.id, file_name=attachment.filename,
                        )
                    )
                credential.imap_last_synced_uid = max(credential.imap_last_synced_uid or 0, email_msg.uid)
                synced_count += 1
            success = True
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            success = False
        duration_ms = int((time.perf_counter() - started) * 1000)

        self.logs.add(
            IntegrationLogEntry(
                company_id=data.company_id, channel_id=channel.id, provider=credential.provider,
                direction=LOG_DIRECTION_OUTBOUND, action="imap_sync",
                success=success, error_message=error_message, duration_ms=duration_ms,
                payload={"synced_count": synced_count},
            )
        )
        self.db.flush()

        if not success:
            raise ProviderConfigurationError(error_message or "IMAP sync failed")

        event_bus.publish(
            Event(
                name=comm_events.IMAP_MAILBOX_SYNCED,
                company_id=data.company_id,
                payload={"channel_id": str(channel.id), "synced_count": synced_count},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return {"synced_count": synced_count}


def _store_email_attachment(*, company_id, uploaded_by, message_id, filename: str, content: bytes, mime_type: str):
    from core.storage.client import new_storage_key, storage_client
    from core.storage.models import Document

    key = new_storage_key(company_id, "communication", filename)
    storage_client.upload(key=key, content=content, mime_type=mime_type or "application/octet-stream")
    return Document(
        company_id=company_id, module="communication", related_entity_type="message",
        related_entity_id=message_id, storage_path=key, mime_type=mime_type or "application/octet-stream",
        uploaded_by=uploaded_by,
    )


class UpdateMessageDeliveryStatusUseCase:
    """Applies a delivery/read status callback from a real provider's
    webhook (Meta's `statuses` payload, Twilio's `MessageStatus` callback)
    onto the originally-sent Message row, matched by external_message_id.
    `actor_user_id` is the channel's `created_by` (see webhook_use_cases.py)
    since a provider callback has no authenticated human actor of its own,
    but AuditLog.actor_user_id is NOT NULL by design -- attributing the
    automated update to whoever configured the channel is the same
    resolution ReceiveInboundMessageUseCase already relies on for
    webhook-originated inbound messages."""

    def __init__(self, db: Session):
        self.db = db
        self.messages = MessageRepository(db)

    def execute(self, data: UpdateMessageDeliveryStatusInput) -> Optional[Any]:
        if data.new_status not in VALID_MESSAGE_STATUSES:
            return None

        from sqlalchemy import select

        from modules.communication.infrastructure.models.message import Message

        message = self.db.scalar(
            select(Message).where(
                Message.company_id == data.company_id, Message.external_message_id == data.external_message_id
            )
        )
        if message is None or message.status == data.new_status:
            return message

        old_status = message.status
        message.status = data.new_status
        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="message.delivery_status_updated",
            entity_type="message",
            entity_id=message.id,
            diff={"old": old_status, "new": data.new_status},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.MESSAGE_DELIVERY_STATUS_UPDATED,
                company_id=data.company_id,
                payload={"message_id": str(message.id), "old_status": old_status, "new_status": data.new_status},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return message
