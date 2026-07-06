"""Resolves a channel to its ChannelProvider implementation.

Every channel type maps to NullChannelProvider *by default* -- a channel
only gets a real provider once a company explicitly configures credentials
for it (ChannelCredential), which is what upgrades it to a real integration.
This is what keeps every pre-2.9 behavior (and every pre-2.9 test) working
completely unchanged: no credential row means no behavior change at all.

Swapping a channel type onto a real integration is entirely a matter of
`ChannelCredential.provider` + config -- no change to any use case or to
core. `get_provider_for_channel()`'s signature gained an optional `config`
parameter in Version 2.9 to carry per-channel decrypted credentials (real
providers are necessarily per-channel-configured, unlike the AI module's
stateless global providers) -- the `ChannelProvider` ABC itself
(`send()`/`test_connection()`) is completely unchanged.
"""
from typing import Any, Dict, Optional, Type

from modules.communication.domain.value_objects import (
    PROVIDER_META_INSTAGRAM,
    PROVIDER_META_MESSENGER,
    PROVIDER_META_WHATSAPP,
    PROVIDER_SMTP,
    PROVIDER_TWILIO_SMS,
    PROVIDER_WEBHOOK,
)
from modules.communication.infrastructure.providers.base import ChannelProvider
from modules.communication.infrastructure.providers.instagram_provider import MetaInstagramProvider
from modules.communication.infrastructure.providers.messenger_provider import MetaMessengerProvider
from modules.communication.infrastructure.providers.null_provider import NullChannelProvider
from modules.communication.infrastructure.providers.smtp_provider import SMTPEmailProvider
from modules.communication.infrastructure.providers.twilio_sms_provider import TwilioSMSProvider
from modules.communication.infrastructure.providers.webhook_provider import GenericWebhookProvider
from modules.communication.infrastructure.providers.whatsapp_provider import MetaWhatsAppProvider

_NULL_PROVIDER = NullChannelProvider()

_PROVIDER_CLASSES: Dict[str, Type[ChannelProvider]] = {
    PROVIDER_META_WHATSAPP: MetaWhatsAppProvider,
    PROVIDER_META_INSTAGRAM: MetaInstagramProvider,
    PROVIDER_META_MESSENGER: MetaMessengerProvider,
    PROVIDER_SMTP: SMTPEmailProvider,
    PROVIDER_TWILIO_SMS: TwilioSMSProvider,
    PROVIDER_WEBHOOK: GenericWebhookProvider,
}


def get_provider_for_channel(
    channel_type: str, *, provider_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None
) -> ChannelProvider:
    """`channel_type` is kept as the first positional argument for backward
    compatibility with every pre-2.9 call site; passing neither
    `provider_name` nor `config` returns exactly the same NullChannelProvider
    singleton every existing caller already gets."""
    if not provider_name or config is None:
        return _NULL_PROVIDER
    provider_cls = _PROVIDER_CLASSES.get(provider_name)
    if provider_cls is None:
        return _NULL_PROVIDER
    return provider_cls(config=config)
