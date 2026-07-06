"""Channel use cases: configuring the inboxes a company sends/receives
through. Create/update only -- a channel is never hard-deleted, only
deactivated (is_active=False), so historical conversations/messages always
keep a valid channel reference."""
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.communication.application.dtos import CreateChannelInput, UpdateChannelInput
from modules.communication.domain import events as comm_events
from modules.communication.domain.value_objects import VALID_CHANNEL_TYPES
from modules.communication.infrastructure.models.channel import Channel
from modules.communication.infrastructure.repositories.channel_repository import ChannelRepository

MODULE_NAME = "communication"


class CreateChannelUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.channels = ChannelRepository(db)

    def execute(self, data: CreateChannelInput) -> Channel:
        if data.channel_type not in VALID_CHANNEL_TYPES:
            raise ValidationAPIError(
                f"Invalid channel_type '{data.channel_type}'",
                details=[{"field": "channel_type", "issue": f"must be one of {sorted(VALID_CHANNEL_TYPES)}"}],
            )

        channel = Channel(
            company_id=data.company_id,
            channel_type=data.channel_type,
            display_name=data.display_name,
            identifier=data.identifier,
            created_by=data.actor_user_id,
        )
        self.channels.add(channel)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="channel.created",
            entity_type="channel",
            entity_id=channel.id,
            diff={"channel_type": channel.channel_type, "display_name": channel.display_name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=comm_events.CHANNEL_CREATED,
                company_id=data.company_id,
                payload={"channel_id": str(channel.id), "channel_type": channel.channel_type},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return channel


class UpdateChannelUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.channels = ChannelRepository(db)

    def execute(self, data: UpdateChannelInput) -> Channel:
        channel = self.channels.get(company_id=data.company_id, channel_id=data.channel_id)
        if channel is None:
            raise NotFoundError("Channel not found")

        diff = {}
        if data.display_name is not None and data.display_name != channel.display_name:
            diff["display_name"] = {"old": channel.display_name, "new": data.display_name}
            channel.display_name = data.display_name
        if data.identifier is not None and data.identifier != channel.identifier:
            diff["identifier"] = {"old": channel.identifier, "new": data.identifier}
            channel.identifier = data.identifier
        if data.is_active is not None and data.is_active != channel.is_active:
            diff["is_active"] = {"old": channel.is_active, "new": data.is_active}
            channel.is_active = data.is_active

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="channel.updated",
            entity_type="channel",
            entity_id=channel.id,
            diff=diff,
        )
        self.db.flush()
        return channel
