"""Inbound webhook processing for every real provider. Every use case here
follows the same shape: verify the provider's signature against the
channel's configured secret, normalize the provider-specific payload into
either a new inbound message (reusing the existing ReceiveInboundMessageUseCase
unchanged) or a delivery/read status update (UpdateMessageDeliveryStatusUseCase),
and log the attempt to IntegrationLogEntry regardless of outcome so the
Webhook Monitor admin page has a complete record -- including rejected/
invalid-signature deliveries, which are a real operational signal (a
misconfigured secret, a spoofing attempt) worth surfacing, not silently
dropping.

None of this is wired through require_permission -- external providers don't
carry our JWTs. Trust comes entirely from the signature check, exactly as
the original inbound.py docstring anticipated: "once a real provider exists,
its webhook handler would call ReceiveInboundMessageUseCase directly
instead, under its own signature-verification, not this route."
"""
import time
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from modules.communication.application.dtos import (
    ReceiveInboundMessageInput,
    UpdateMessageDeliveryStatusInput,
)
from modules.communication.application.use_cases._provider_resolution import decrypt_config
from modules.communication.application.use_cases.conversation_use_cases import ReceiveInboundMessageUseCase
from modules.communication.application.use_cases.integration_use_cases import UpdateMessageDeliveryStatusUseCase
from modules.communication.domain.exceptions import ProviderConfigurationError, WebhookSignatureError
from modules.communication.domain.value_objects import LOG_DIRECTION_INBOUND
from modules.communication.infrastructure.models.integration_log_entry import IntegrationLogEntry
from modules.communication.infrastructure.providers.meta_client import verify_meta_signature
from modules.communication.infrastructure.providers.twilio_sms_provider import verify_twilio_signature
from modules.communication.infrastructure.providers.webhook_provider import verify_webhook_signature
from modules.communication.infrastructure.repositories.channel_credential_repository import (
    ChannelCredentialRepository,
)
from modules.communication.infrastructure.repositories.channel_repository import ChannelRepository
from modules.communication.infrastructure.repositories.integration_log_repository import IntegrationLogRepository

MODULE_NAME = "communication"


class _BaseWebhookUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.channels = ChannelRepository(db)
        self.credentials = ChannelCredentialRepository(db)
        self.logs = IntegrationLogRepository(db)

    def _load_channel_and_credential(self, channel_id):
        """Webhooks are public (no authenticated active-company context), so
        the channel is looked up by id alone, and company_id is taken from
        the resolved row -- never trusted from the request."""
        channel = self.channels.get_by_id_any_company(channel_id)
        if channel is None:
            raise NotFoundError("Channel not found")
        credential = self.credentials.get_by_channel(company_id=channel.company_id, channel_id=channel_id)
        if credential is None:
            raise NotFoundError("No credential configured for this channel")
        if channel.created_by is None:
            # AuditLog.actor_user_id is NOT NULL -- a webhook-originated write
            # is attributed to whoever configured the channel, since there's
            # no authenticated human actor for an external provider callback.
            raise ProviderConfigurationError(
                "This channel has no created_by user to attribute webhook-originated writes to"
            )
        return channel, credential

    def _log(self, *, company_id, channel_id, provider, success, signature_valid, error_message, payload, started):
        duration_ms = int((time.perf_counter() - started) * 1000)
        self.logs.add(
            IntegrationLogEntry(
                company_id=company_id, channel_id=channel_id, provider=provider,
                direction=LOG_DIRECTION_INBOUND, action="receive_webhook",
                success=success, signature_valid=signature_valid, error_message=error_message,
                duration_ms=duration_ms, payload=payload,
            )
        )
        self.db.flush()


class ReceiveMetaWebhookUseCase(_BaseWebhookUseCase):
    """Handles WhatsApp Business Cloud API, Instagram Messaging API, and
    Messenger Platform webhooks -- all three ride the same Meta Graph API
    webhook envelope (`entry[].changes[]` for WhatsApp,
    `entry[].messaging[]` for Instagram/Messenger)."""

    def execute(
        self, *, channel_id, raw_body: bytes, signature_header: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        channel, credential = self._load_channel_and_credential(channel_id)

        config = decrypt_config(credential)
        app_secret = config.get("app_secret", "")
        signature_valid = verify_meta_signature(app_secret=app_secret, raw_body=raw_body, signature_header=signature_header)

        if not signature_valid:
            self._log(
                company_id=channel.company_id, channel_id=channel_id, provider=credential.provider,
                success=False, signature_valid=False, error_message="Invalid signature", payload=payload,
                started=started,
            )
            raise WebhookSignatureError("Meta webhook signature verification failed")

        created_messages = 0
        updated_statuses = 0
        error_message: Optional[str] = None
        try:
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    created_messages += self._process_whatsapp_value(channel, value)
                    updated_statuses += self._process_whatsapp_statuses(channel, value)
                for messaging_event in entry.get("messaging", []):
                    created_messages += self._process_messenger_event(channel, messaging_event)
            success = True
        except Exception as exc:  # noqa: BLE001 -- log and re-raise so the endpoint still 200s per provider expectations
            error_message = str(exc)
            success = False

        self._log(
            company_id=channel.company_id, channel_id=channel_id, provider=credential.provider,
            success=success, signature_valid=True, error_message=error_message, payload=payload, started=started,
        )
        return {"created_messages": created_messages, "updated_statuses": updated_statuses}

    def _process_whatsapp_value(self, channel, value: Dict[str, Any]) -> int:
        messages = value.get("messages") or []
        if not messages:
            return 0
        contacts = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts") or []}
        count = 0
        for msg in messages:
            from_id = msg.get("from")
            body = self._extract_whatsapp_body(msg)
            ReceiveInboundMessageUseCase(self.db).execute(
                ReceiveInboundMessageInput(
                    company_id=channel.company_id, actor_user_id=channel.created_by,
                    channel_id=channel.id, external_contact_id=from_id,
                    external_contact_name=contacts.get(from_id), body=body,
                    message_type=msg.get("type", "text"), external_message_id=msg.get("id"),
                )
            )
            count += 1
        return count

    @staticmethod
    def _extract_whatsapp_body(msg: Dict[str, Any]) -> str:
        msg_type = msg.get("type", "text")
        if msg_type == "text":
            return msg.get("text", {}).get("body", "")
        media_obj = msg.get(msg_type, {})
        return media_obj.get("id") or media_obj.get("link") or ""

    def _process_whatsapp_statuses(self, channel, value: Dict[str, Any]) -> int:
        statuses = value.get("statuses") or []
        count = 0
        for status in statuses:
            new_status = {"sent": "sent", "delivered": "delivered", "read": "read", "failed": "failed"}.get(
                status.get("status"), None
            )
            if not new_status:
                continue
            UpdateMessageDeliveryStatusUseCase(self.db).execute(
                UpdateMessageDeliveryStatusInput(
                    company_id=channel.company_id, actor_user_id=channel.created_by,
                    external_message_id=status.get("id"), new_status=new_status, channel_id=channel.id,
                )
            )
            count += 1
        return count

    def _process_messenger_event(self, channel, event: Dict[str, Any]) -> int:
        message = event.get("message")
        if not message:
            return 0
        sender_id = event.get("sender", {}).get("id")
        body = message.get("text") or ""
        if not body and message.get("attachments"):
            body = message["attachments"][0].get("payload", {}).get("url", "")
        ReceiveInboundMessageUseCase(self.db).execute(
            ReceiveInboundMessageInput(
                company_id=channel.company_id, actor_user_id=channel.created_by,
                channel_id=channel.id, external_contact_id=sender_id, body=body,
                message_type="text" if message.get("text") else "image",
                external_message_id=message.get("mid"),
            )
        )
        return 1


class ReceiveTwilioWebhookUseCase(_BaseWebhookUseCase):
    def execute(
        self, *, channel_id, url: str, form_params: Dict[str, str], signature_header: Optional[str]
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        channel, credential = self._load_channel_and_credential(channel_id)

        config = decrypt_config(credential)
        signature_valid = verify_twilio_signature(
            auth_token=config.get("auth_token", ""), url=url, form_params=form_params, signature_header=signature_header
        )
        if not signature_valid:
            self._log(
                company_id=channel.company_id, channel_id=channel_id, provider=credential.provider,
                success=False, signature_valid=False, error_message="Invalid signature", payload=form_params,
                started=started,
            )
            raise WebhookSignatureError("Twilio webhook signature verification failed")

        error_message: Optional[str] = None
        created = 0
        updated = 0
        try:
            message_status = form_params.get("MessageStatus")
            message_sid = form_params.get("MessageSid") or form_params.get("SmsSid")
            if message_status:
                new_status = {"delivered": "delivered", "read": "read", "failed": "failed", "undelivered": "failed", "sent": "sent"}.get(
                    message_status
                )
                if new_status and message_sid:
                    UpdateMessageDeliveryStatusUseCase(self.db).execute(
                        UpdateMessageDeliveryStatusInput(
                            company_id=channel.company_id, actor_user_id=channel.created_by,
                            external_message_id=message_sid, new_status=new_status, channel_id=channel.id,
                        )
                    )
                    updated = 1
            else:
                ReceiveInboundMessageUseCase(self.db).execute(
                    ReceiveInboundMessageInput(
                        company_id=channel.company_id, actor_user_id=channel.created_by,
                        channel_id=channel.id, external_contact_id=form_params.get("From", ""),
                        body=form_params.get("Body", ""), external_message_id=message_sid,
                    )
                )
                created = 1
            success = True
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            success = False

        self._log(
            company_id=channel.company_id, channel_id=channel_id, provider=credential.provider,
            success=success, signature_valid=True, error_message=error_message, payload=form_params, started=started,
        )
        return {"created_messages": created, "updated_statuses": updated}


class ReceiveGenericWebhookUseCase(_BaseWebhookUseCase):
    """Normalized inbound shape for the generic webhook provider:
    {"external_contact_id": ..., "external_contact_name": ..., "body": ...,
    "message_type": ...} for a new message, or
    {"external_message_id": ..., "status": ...} for a delivery update."""

    def execute(self, *, channel_id, raw_body: bytes, signature_header: Optional[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        started = time.perf_counter()
        channel, credential = self._load_channel_and_credential(channel_id)

        config = decrypt_config(credential)
        signature_valid = verify_webhook_signature(
            secret=config.get("secret", ""), raw_body=raw_body, signature_header=signature_header
        )
        if not signature_valid:
            self._log(
                company_id=channel.company_id, channel_id=channel_id, provider=credential.provider,
                success=False, signature_valid=False, error_message="Invalid signature", payload=payload,
                started=started,
            )
            raise WebhookSignatureError("Webhook signature verification failed")

        error_message: Optional[str] = None
        created = 0
        updated = 0
        try:
            if payload.get("external_message_id") and payload.get("status"):
                UpdateMessageDeliveryStatusUseCase(self.db).execute(
                    UpdateMessageDeliveryStatusInput(
                        company_id=channel.company_id, actor_user_id=channel.created_by,
                        external_message_id=payload["external_message_id"], new_status=payload["status"],
                        channel_id=channel.id,
                    )
                )
                updated = 1
            elif payload.get("external_contact_id"):
                ReceiveInboundMessageUseCase(self.db).execute(
                    ReceiveInboundMessageInput(
                        company_id=channel.company_id, actor_user_id=channel.created_by,
                        channel_id=channel.id, external_contact_id=payload["external_contact_id"],
                        external_contact_name=payload.get("external_contact_name"),
                        body=payload.get("body", ""), message_type=payload.get("message_type"),
                    )
                )
                created = 1
            success = True
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            success = False

        self._log(
            company_id=channel.company_id, channel_id=channel_id, provider=credential.provider,
            success=success, signature_valid=True, error_message=error_message, payload=payload, started=started,
        )
        return {"created_messages": created, "updated_statuses": updated}
