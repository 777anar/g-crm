"""Resolves a channel type to its ChannelProvider implementation.

Every channel type maps to NullChannelProvider today (see its docstring for
why: no real WhatsApp/Meta/email/SMS integration exists yet, by explicit
design). Swapping one channel type onto a real integration later is a
one-line change to `_PROVIDERS_BY_CHANNEL_TYPE` below -- e.g.
`CHANNEL_TYPE_WHATSAPP: WhatsAppCloudAPIProvider(...)` -- with no change to
any use case or to core.
"""
from typing import Dict

from modules.communication.domain.value_objects import (
    CHANNEL_TYPE_EMAIL,
    CHANNEL_TYPE_INSTAGRAM,
    CHANNEL_TYPE_MESSENGER,
    CHANNEL_TYPE_SMS,
    CHANNEL_TYPE_WHATSAPP,
)
from modules.communication.infrastructure.providers.base import ChannelProvider
from modules.communication.infrastructure.providers.null_provider import NullChannelProvider

_NULL_PROVIDER = NullChannelProvider()

_PROVIDERS_BY_CHANNEL_TYPE: Dict[str, ChannelProvider] = {
    CHANNEL_TYPE_WHATSAPP: _NULL_PROVIDER,
    CHANNEL_TYPE_INSTAGRAM: _NULL_PROVIDER,
    CHANNEL_TYPE_MESSENGER: _NULL_PROVIDER,
    CHANNEL_TYPE_EMAIL: _NULL_PROVIDER,
    CHANNEL_TYPE_SMS: _NULL_PROVIDER,
}


def get_provider_for_channel(channel_type: str) -> ChannelProvider:
    return _PROVIDERS_BY_CHANNEL_TYPE.get(channel_type, _NULL_PROVIDER)
