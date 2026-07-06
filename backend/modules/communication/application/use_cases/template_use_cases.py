"""Message template / quick-reply use cases."""
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.communication.application.dtos import CreateMessageTemplateInput, UpdateMessageTemplateInput
from modules.communication.domain import events as comm_events
from modules.communication.domain.value_objects import VALID_CHANNEL_TYPES
from modules.communication.infrastructure.models.message_template import MessageTemplate
from modules.communication.infrastructure.repositories.message_template_repository import (
    MessageTemplateRepository,
)

MODULE_NAME = "communication"


def _validate_channel_type(channel_type):
    if channel_type is not None and channel_type not in VALID_CHANNEL_TYPES:
        raise ValidationAPIError(
            f"Invalid channel_type '{channel_type}'",
            details=[{"field": "channel_type", "issue": f"must be one of {sorted(VALID_CHANNEL_TYPES)}"}],
        )


class CreateMessageTemplateUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.templates = MessageTemplateRepository(db)

    def execute(self, data: CreateMessageTemplateInput) -> MessageTemplate:
        _validate_channel_type(data.channel_type)

        template = MessageTemplate(
            company_id=data.company_id,
            name=data.name,
            body=data.body,
            channel_type=data.channel_type,
            shortcut=data.shortcut,
            created_by=data.actor_user_id,
        )
        self.templates.add(template)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="message_template.created",
            entity_type="message_template",
            entity_id=template.id,
            diff={"name": template.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.MESSAGE_TEMPLATE_CREATED,
                company_id=data.company_id,
                payload={"template_id": str(template.id), "name": template.name},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return template


class UpdateMessageTemplateUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.templates = MessageTemplateRepository(db)

    def execute(self, data: UpdateMessageTemplateInput) -> MessageTemplate:
        template = self.templates.get(company_id=data.company_id, template_id=data.template_id)
        if template is None:
            raise NotFoundError("Message template not found")

        _validate_channel_type(data.channel_type)

        diff = {}
        if data.name is not None and data.name != template.name:
            diff["name"] = {"old": template.name, "new": data.name}
            template.name = data.name
        if data.body is not None and data.body != template.body:
            diff["body"] = {"old": template.body, "new": data.body}
            template.body = data.body
        if data.channel_type is not None and data.channel_type != template.channel_type:
            diff["channel_type"] = {"old": template.channel_type, "new": data.channel_type}
            template.channel_type = data.channel_type
        if data.shortcut is not None and data.shortcut != template.shortcut:
            diff["shortcut"] = {"old": template.shortcut, "new": data.shortcut}
            template.shortcut = data.shortcut
        if data.is_active is not None and data.is_active != template.is_active:
            diff["is_active"] = {"old": template.is_active, "new": data.is_active}
            template.is_active = data.is_active

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="message_template.updated",
            entity_type="message_template",
            entity_id=template.id,
            diff=diff,
        )
        self.db.flush()
        return template
