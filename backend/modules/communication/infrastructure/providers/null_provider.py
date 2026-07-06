import uuid

from modules.communication.infrastructure.providers.base import ChannelProvider


class NullChannelProvider(ChannelProvider):
    """The only provider registered today, for every channel type. Per this
    phase's explicit scope, it does not call out to WhatsApp, Instagram,
    Messenger, or any real email/SMS gateway -- it simulates a successful
    send by minting a local id, so the rest of the system (Message.status,
    Message.external_message_id, Conversation.last_message_at/preview)
    behaves exactly as it will once a real provider is plugged in behind
    the same ChannelProvider interface."""

    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        return f"local-{uuid.uuid4()}"
