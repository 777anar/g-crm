"""Shared helper: builds the real (or Null) ChannelProvider for a Channel by
loading and decrypting its ChannelCredential, if one exists. Used by both
SendMessageUseCase (conversation_use_cases.py) and the integration use cases
(integration_use_cases.py) so the "no credential -> NullChannelProvider,
exactly like before Version 2.9" rule lives in exactly one place.
"""
import json
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.channel import Channel
from modules.communication.infrastructure.models.channel_credential import ChannelCredential
from modules.communication.infrastructure.providers.base import ChannelProvider
from modules.communication.infrastructure.providers.registry import get_provider_for_channel
from modules.communication.infrastructure.repositories.channel_credential_repository import (
    ChannelCredentialRepository,
)
from modules.communication.infrastructure.security.encryption import decrypt_text


def resolve_provider_and_credential(
    db: Session, channel: Channel
) -> Tuple[ChannelProvider, Optional[ChannelCredential]]:
    credential = ChannelCredentialRepository(db).get_by_channel(company_id=channel.company_id, channel_id=channel.id)
    if credential is None:
        return get_provider_for_channel(channel.channel_type), None
    config = json.loads(decrypt_text(credential.encrypted_config))
    provider = get_provider_for_channel(channel.channel_type, provider_name=credential.provider, config=config)
    return provider, credential


def decrypt_config(credential: ChannelCredential) -> dict:
    return json.loads(decrypt_text(credential.encrypted_config))
