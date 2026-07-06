"""Application-layer input DTOs for the Communication Center module."""
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class CreateChannelInput(ActorContext):
    channel_type: str
    display_name: str
    identifier: Optional[str] = None


@dataclass
class UpdateChannelInput(ActorContext):
    channel_id: uuid.UUID
    display_name: Optional[str] = None
    identifier: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass
class GetOrCreateConversationInput(ActorContext):
    channel_id: uuid.UUID
    external_contact_id: str
    external_contact_name: Optional[str] = None


@dataclass
class ReceiveInboundMessageInput(ActorContext):
    channel_id: uuid.UUID
    external_contact_id: str
    body: str
    external_contact_name: Optional[str] = None
    message_type: Optional[str] = None
    external_message_id: Optional[str] = None


@dataclass
class SendMessageInput(ActorContext):
    conversation_id: uuid.UUID
    body: str
    message_type: Optional[str] = None
    template_id: Optional[uuid.UUID] = None


@dataclass
class UpdateConversationInput(ActorContext):
    conversation_id: uuid.UUID
    status: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    tags: Optional[List[str]] = None
    customer_id: Optional[uuid.UUID] = None
    lead_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    quote_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None


@dataclass
class MarkConversationReadInput(ActorContext):
    conversation_id: uuid.UUID


@dataclass
class AddConversationNoteInput(ActorContext):
    conversation_id: uuid.UUID
    body: str


@dataclass
class AddMessageAttachmentInput(ActorContext):
    message_id: uuid.UUID
    document_id: uuid.UUID
    file_name: Optional[str] = None


@dataclass
class CreateMessageTemplateInput(ActorContext):
    name: str
    body: str
    channel_type: Optional[str] = None
    shortcut: Optional[str] = None


@dataclass
class UpdateMessageTemplateInput(ActorContext):
    template_id: uuid.UUID
    name: Optional[str] = None
    body: Optional[str] = None
    channel_type: Optional[str] = None
    shortcut: Optional[str] = None
    is_active: Optional[bool] = None


# ── Real integrations (Version 2.9) ─────────────────────────────────────────


@dataclass
class ConfigureChannelCredentialInput(ActorContext):
    channel_id: uuid.UUID
    provider: str
    config: Dict[str, Any]
    webhook_secret: Optional[str] = None


@dataclass
class TestChannelConnectionInput(ActorContext):
    channel_id: uuid.UUID


@dataclass
class ProcessMessageQueueInput(ActorContext):
    limit: int = 50


@dataclass
class SyncImapMailboxInput(ActorContext):
    channel_id: uuid.UUID


@dataclass
class UpdateMessageDeliveryStatusInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    external_message_id: str
    new_status: str
    channel_id: Optional[uuid.UUID] = None


@dataclass
class ReceiveProviderWebhookInput:
    channel_id: uuid.UUID
    provider: str
    raw_body: bytes
    signature_header: Optional[str]
    parsed_payload: Dict[str, Any]
