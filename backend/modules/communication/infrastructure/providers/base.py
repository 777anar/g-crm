"""The provider seam every real channel integration (WhatsApp Cloud API,
Instagram Graph API, Messenger Platform, an SMTP/email provider, an SMS
gateway) implements.

`SendMessageUseCase` (see application/use_cases/conversation_use_cases.py)
never imports a concrete provider directly -- it always resolves one through
`registry.get_provider_for_channel()`. Plugging in a real integration is
therefore a change to this module's infrastructure layer only (implement
this interface, register it in registry.py): no change to any use case, any
other module, or the core.

Version 2.9 (Real Integrations) added `test_connection()` as a concrete,
non-abstract method with a trivial default -- this is additive only: the
abstract `send()` contract every existing provider (and every pre-2.9 test)
already relies on is completely unchanged, and NullChannelProvider needed no
modification at all to keep working exactly as before.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class ChannelProvider(ABC):
    @abstractmethod
    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        """Sends one outbound message to `external_contact_id` (the
        recipient's address on this channel -- a phone number, an IG/PSID
        handle, an email address, ...) and returns a provider-assigned
        external message id."""
        raise NotImplementedError

    def test_connection(self) -> Dict[str, Any]:
        """Verifies this provider's credentials actually work against the
        real service, without sending a message. Returns
        {"ok": bool, "detail": str}. The default (used by NullChannelProvider
        and any provider that doesn't override it) always succeeds trivially
        -- there's nothing to verify when there's no real integration."""
        return {"ok": True, "detail": "No real provider configured; nothing to verify."}
