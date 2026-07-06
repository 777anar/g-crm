"""The provider seam every real channel integration (WhatsApp Cloud API,
Instagram Graph API, Messenger Platform, an SMTP/email provider, an SMS
gateway) will implement later.

`SendMessageUseCase` (see application/use_cases/conversation_use_cases.py)
never imports a concrete provider directly -- it always resolves one through
`registry.get_provider_for_channel()`. Plugging in a real integration is
therefore a change to this module's infrastructure layer only (implement
this interface, register it in registry.py): no change to any use case, any
other module, or the core.
"""
from abc import ABC, abstractmethod


class ChannelProvider(ABC):
    @abstractmethod
    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        """Sends one outbound message to `external_contact_id` (the
        recipient's address on this channel -- a phone number, an IG/PSID
        handle, an email address, ...) and returns a provider-assigned
        external message id."""
        raise NotImplementedError
