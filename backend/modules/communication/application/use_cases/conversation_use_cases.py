"""Conversation/message use cases: get-or-create a thread for an external
contact (with CRM customer identification and auto-Lead-creation for an
unknown sender), receive an inbound message, send an outbound one (through
the provider abstraction), and manage a conversation's status/assignment/
tags/links, notes, and attachments.

Cross-module reads/writes go through CRM's own repository and use case
directly (CustomerModel lookups, CreateLeadUseCase) -- the same pattern
Production/Installation/Finance use for their own cross-module calls, rather
than the (unused, in this codebase) event-subscription mechanism.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.auth.models import UserCompanyRole
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.communication.application.dtos import (
    AddConversationNoteInput,
    AddMessageAttachmentInput,
    GetOrCreateConversationInput,
    MarkConversationReadInput,
    ReceiveInboundMessageInput,
    SendMessageInput,
    UpdateConversationInput,
)
from modules.communication.domain import events as comm_events
from modules.communication.domain.exceptions import ChannelInactiveError
from modules.communication.domain.value_objects import (
    CHANNEL_CUSTOMER_FIELD,
    CHANNEL_LEAD_SOURCE,
    CONVERSATION_STATUS_CLOSED,
    CONVERSATION_STATUS_OPEN,
    DEFAULT_MESSAGE_TYPE,
    MESSAGE_DIRECTION_INBOUND,
    MESSAGE_DIRECTION_OUTBOUND,
    MESSAGE_STATUS_RECEIVED,
    MESSAGE_STATUS_SENT,
    SENDER_TYPE_AGENT,
    SENDER_TYPE_CUSTOMER,
    VALID_CONVERSATION_STATUSES,
)
from modules.communication.infrastructure.models.conversation import Conversation
from modules.communication.infrastructure.models.conversation_note import ConversationNote
from modules.communication.infrastructure.models.message import Message
from modules.communication.infrastructure.models.message_attachment import MessageAttachment
from modules.communication.infrastructure.providers.registry import get_provider_for_channel
from modules.communication.infrastructure.repositories.channel_repository import ChannelRepository
from modules.communication.infrastructure.repositories.conversation_note_repository import (
    ConversationNoteRepository,
)
from modules.communication.infrastructure.repositories.conversation_repository import ConversationRepository
from modules.communication.infrastructure.repositories.message_attachment_repository import (
    MessageAttachmentRepository,
)
from modules.communication.infrastructure.repositories.message_repository import MessageRepository
from modules.crm.application.dtos import CreateLeadInput
from modules.crm.application.use_cases import CreateLeadUseCase
from modules.crm.infrastructure.models.customer import Customer as CustomerModel

MODULE_NAME = "communication"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_user_belongs_to_company(db: Session, *, company_id: uuid.UUID, user_id: uuid.UUID) -> None:
    exists = db.scalar(
        select(UserCompanyRole.id).where(
            UserCompanyRole.company_id == company_id, UserCompanyRole.user_id == user_id
        )
    )
    if exists is None:
        raise ValidationAPIError(
            "assigned_to does not refer to a member of this company",
            details=[{"field": "assigned_to", "issue": "no such user in this company"}],
        )


def _identify_customer(
    db: Session, *, company_id: uuid.UUID, channel_type: str, external_contact_id: str
) -> Optional[CustomerModel]:
    """Matches an inbound sender against an existing CRM Customer, using the
    field the channel's identity naturally maps onto -- see
    domain.value_objects.CHANNEL_CUSTOMER_FIELD."""
    field_name = CHANNEL_CUSTOMER_FIELD.get(channel_type)
    if not field_name or not external_contact_id:
        return None
    column = getattr(CustomerModel, field_name)
    return db.scalar(
        select(CustomerModel).where(
            CustomerModel.company_id == company_id,
            CustomerModel.deleted_at.is_(None),
            column == external_contact_id,
        )
    )


class GetOrCreateConversationUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.channels = ChannelRepository(db)
        self.conversations = ConversationRepository(db)

    def execute(self, data: GetOrCreateConversationInput) -> Conversation:
        channel = self.channels.get(company_id=data.company_id, channel_id=data.channel_id)
        if channel is None:
            raise NotFoundError("Channel not found")

        existing = self.conversations.get_by_external_contact(
            company_id=data.company_id, channel_id=data.channel_id, external_contact_id=data.external_contact_id
        )
        if existing is not None:
            if data.external_contact_name and data.external_contact_name != existing.external_contact_name:
                existing.external_contact_name = data.external_contact_name
                self.db.flush()
            return existing

        customer = _identify_customer(
            self.db,
            company_id=data.company_id,
            channel_type=channel.channel_type,
            external_contact_id=data.external_contact_id,
        )

        lead = None
        if customer is None:
            # Unknown sender -- capture them as a Lead rather than letting the
            # conversation float with no CRM record at all, per this module's
            # "Auto-create Lead if sender is unknown" requirement. Reuses
            # CRM's CreateLeadUseCase directly, exactly the extension point
            # its own docstring calls out for a future channel webhook.
            field_name = CHANNEL_CUSTOMER_FIELD.get(channel.channel_type)
            lead_contact = {}
            if field_name == "email":
                lead_contact["email"] = data.external_contact_id
            elif field_name in ("phone", "whatsapp"):
                lead_contact["phone"] = data.external_contact_id
            lead = CreateLeadUseCase(self.db).execute(
                CreateLeadInput(
                    company_id=data.company_id,
                    actor_user_id=data.actor_user_id,
                    full_name=data.external_contact_name or data.external_contact_id,
                    source_channel=CHANNEL_LEAD_SOURCE.get(channel.channel_type, "other"),
                    **lead_contact,
                )
            )

        conversation = Conversation(
            company_id=data.company_id,
            channel_id=channel.id,
            customer_id=customer.id if customer else None,
            lead_id=lead.id if lead else None,
            external_contact_id=data.external_contact_id,
            external_contact_name=data.external_contact_name,
            created_by=data.actor_user_id,
        )
        self.conversations.add(conversation)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="conversation.created",
            entity_type="conversation",
            entity_id=conversation.id,
            diff={
                "channel_id": str(channel.id),
                "customer_id": str(customer.id) if customer else None,
                "lead_id": str(lead.id) if lead else None,
            },
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.CONVERSATION_CREATED,
                company_id=data.company_id,
                payload={
                    "conversation_id": str(conversation.id),
                    "customer_id": str(customer.id) if customer else None,
                    "lead_id": str(lead.id) if lead else None,
                },
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return conversation


class ReceiveInboundMessageUseCase:
    """Stands in for a future real channel webhook -- see
    infrastructure/providers/base.py. Exposed today as an authenticated API
    endpoint an agent (or, later, a real webhook handler) calls with the
    inbound payload, rather than a public unauthenticated route, since no
    signature-verified real webhook exists yet."""

    def __init__(self, db: Session):
        self.db = db
        self.messages = MessageRepository(db)

    def execute(self, data: ReceiveInboundMessageInput) -> Message:
        conversation = GetOrCreateConversationUseCase(self.db).execute(
            GetOrCreateConversationInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                channel_id=data.channel_id,
                external_contact_id=data.external_contact_id,
                external_contact_name=data.external_contact_name,
            )
        )

        old_status = conversation.status
        if conversation.status == CONVERSATION_STATUS_CLOSED:
            conversation.status = CONVERSATION_STATUS_OPEN

        message = Message(
            company_id=data.company_id,
            conversation_id=conversation.id,
            direction=MESSAGE_DIRECTION_INBOUND,
            sender_type=SENDER_TYPE_CUSTOMER,
            message_type=data.message_type or DEFAULT_MESSAGE_TYPE,
            body=data.body,
            external_message_id=data.external_message_id,
            status=MESSAGE_STATUS_RECEIVED,
        )
        self.messages.add(message)

        now = _now()
        conversation.last_message_at = now
        conversation.last_message_preview = (data.body or "")[:300]
        conversation.unread_count = (conversation.unread_count or 0) + 1

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="message.received",
            entity_type="message",
            entity_id=message.id,
            diff={"conversation_id": str(conversation.id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.MESSAGE_RECEIVED,
                company_id=data.company_id,
                payload={"message_id": str(message.id), "conversation_id": str(conversation.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        if old_status != conversation.status:
            event_bus.publish(
                Event(
                    name=comm_events.CONVERSATION_STATUS_CHANGED,
                    company_id=data.company_id,
                    payload={
                        "conversation_id": str(conversation.id),
                        "old_status": old_status,
                        "new_status": conversation.status,
                    },
                    published_by_module=MODULE_NAME,
                ),
                self.db,
            )
        return message


class SendMessageUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.conversations = ConversationRepository(db)
        self.channels = ChannelRepository(db)
        self.messages = MessageRepository(db)

    def execute(self, data: SendMessageInput) -> Message:
        conversation = self.conversations.get(company_id=data.company_id, conversation_id=data.conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        channel = self.channels.get(company_id=data.company_id, channel_id=conversation.channel_id)
        if channel is None:
            raise NotFoundError("Channel not found")
        if not channel.is_active:
            raise ChannelInactiveError("This channel is deactivated and cannot send messages")

        message_type = data.message_type or DEFAULT_MESSAGE_TYPE
        provider = get_provider_for_channel(channel.channel_type)
        external_message_id = provider.send(
            channel=channel,
            external_contact_id=conversation.external_contact_id,
            body=data.body,
            message_type=message_type,
        )

        message = Message(
            company_id=data.company_id,
            conversation_id=conversation.id,
            direction=MESSAGE_DIRECTION_OUTBOUND,
            sender_type=SENDER_TYPE_AGENT,
            sender_user_id=data.actor_user_id,
            message_type=message_type,
            body=data.body,
            template_id=data.template_id,
            external_message_id=external_message_id,
            status=MESSAGE_STATUS_SENT,
        )
        self.messages.add(message)

        conversation.last_message_at = _now()
        conversation.last_message_preview = (data.body or "")[:300]

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="message.sent",
            entity_type="message",
            entity_id=message.id,
            diff={"conversation_id": str(conversation.id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.MESSAGE_SENT,
                company_id=data.company_id,
                payload={"message_id": str(message.id), "conversation_id": str(conversation.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return message


class UpdateConversationUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.conversations = ConversationRepository(db)

    def execute(self, data: UpdateConversationInput) -> Conversation:
        conversation = self.conversations.get(company_id=data.company_id, conversation_id=data.conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found")

        diff = {}
        old_status = conversation.status
        if data.status is not None and data.status != conversation.status:
            if data.status not in VALID_CONVERSATION_STATUSES:
                raise ValidationAPIError(
                    f"Invalid status '{data.status}'",
                    details=[{"field": "status", "issue": f"must be one of {sorted(VALID_CONVERSATION_STATUSES)}"}],
                )
            diff["status"] = {"old": conversation.status, "new": data.status}
            conversation.status = data.status

        assigned_changed = False
        if data.assigned_to is not None and data.assigned_to != conversation.assigned_to:
            _ensure_user_belongs_to_company(self.db, company_id=data.company_id, user_id=data.assigned_to)
            diff["assigned_to"] = {
                "old": str(conversation.assigned_to) if conversation.assigned_to else None,
                "new": str(data.assigned_to),
            }
            conversation.assigned_to = data.assigned_to
            assigned_changed = True

        if data.tags is not None and data.tags != list(conversation.tags or []):
            diff["tags"] = {"old": conversation.tags, "new": data.tags}
            conversation.tags = data.tags

        linked_changed = False
        for field_name in ("customer_id", "lead_id", "project_id", "quote_id", "order_id"):
            new_value = getattr(data, field_name)
            if new_value is not None and new_value != getattr(conversation, field_name):
                old_value = getattr(conversation, field_name)
                diff[field_name] = {"old": str(old_value) if old_value else None, "new": str(new_value)}
                setattr(conversation, field_name, new_value)
                linked_changed = True

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="conversation.updated",
            entity_type="conversation",
            entity_id=conversation.id,
            diff=diff,
        )
        self.db.flush()

        if "status" in diff:
            event_bus.publish(
                Event(
                    name=comm_events.CONVERSATION_STATUS_CHANGED,
                    company_id=data.company_id,
                    payload={
                        "conversation_id": str(conversation.id),
                        "old_status": old_status,
                        "new_status": conversation.status,
                    },
                    published_by_module=MODULE_NAME,
                ),
                self.db,
            )
        if assigned_changed:
            event_bus.publish(
                Event(
                    name=comm_events.CONVERSATION_ASSIGNED,
                    company_id=data.company_id,
                    payload={"conversation_id": str(conversation.id), "assigned_to": str(conversation.assigned_to)},
                    published_by_module=MODULE_NAME,
                ),
                self.db,
            )
        if linked_changed:
            event_bus.publish(
                Event(
                    name=comm_events.CONVERSATION_LINKED,
                    company_id=data.company_id,
                    payload={"conversation_id": str(conversation.id)},
                    published_by_module=MODULE_NAME,
                ),
                self.db,
            )
        return conversation


class MarkConversationReadUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.conversations = ConversationRepository(db)

    def execute(self, data: MarkConversationReadInput) -> Conversation:
        conversation = self.conversations.get(company_id=data.company_id, conversation_id=data.conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        if conversation.unread_count:
            conversation.unread_count = 0
            record_audit(
                self.db,
                company_id=data.company_id,
                module=MODULE_NAME,
                actor_user_id=data.actor_user_id,
                action="conversation.read",
                entity_type="conversation",
                entity_id=conversation.id,
            )
            self.db.flush()
        return conversation


class AddConversationNoteUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.conversations = ConversationRepository(db)
        self.notes = ConversationNoteRepository(db)

    def execute(self, data: AddConversationNoteInput) -> ConversationNote:
        conversation = self.conversations.get(company_id=data.company_id, conversation_id=data.conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found")

        note = ConversationNote(
            company_id=data.company_id,
            conversation_id=conversation.id,
            body=data.body,
            created_by=data.actor_user_id,
        )
        self.notes.add(note)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="conversation.note_added",
            entity_type="conversation_note",
            entity_id=note.id,
            diff={"conversation_id": str(conversation.id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.CONVERSATION_NOTE_ADDED,
                company_id=data.company_id,
                payload={"conversation_id": str(conversation.id), "note_id": str(note.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return note


class AddMessageAttachmentUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.messages = MessageRepository(db)
        self.attachments = MessageAttachmentRepository(db)

    def execute(self, data: AddMessageAttachmentInput) -> MessageAttachment:
        message = self.messages.get(company_id=data.company_id, message_id=data.message_id)
        if message is None:
            raise NotFoundError("Message not found")

        attachment = MessageAttachment(
            company_id=data.company_id,
            message_id=message.id,
            document_id=data.document_id,
            file_name=data.file_name,
        )
        self.attachments.add(attachment)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="message.attachment_added",
            entity_type="message_attachment",
            entity_id=attachment.id,
            diff={"message_id": str(message.id)},
        )
        self.db.flush()
        return attachment
