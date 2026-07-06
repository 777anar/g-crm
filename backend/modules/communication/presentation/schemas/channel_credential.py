import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from modules.communication.domain.value_objects import VALID_PROVIDERS

_SECRET_FIELD_MARKERS = ("token", "password", "secret", "auth_token", "api_key")


def mask_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Never round-trips a real credential value back to the frontend --
    any field whose name looks secret-like is reduced to its last 4
    characters; everything else (host, port, phone_number_id, ...) is
    shown in full since it isn't sensitive and is useful for verifying
    what's actually configured."""
    masked: Dict[str, Any] = {}
    for key, value in config.items():
        if any(marker in key.lower() for marker in _SECRET_FIELD_MARKERS):
            text = str(value)
            masked[key] = f"••••{text[-4:]}" if len(text) > 4 else "••••"
        else:
            masked[key] = value
    return masked


class ChannelCredentialConfigure(BaseModel):
    provider: str
    config: Dict[str, Any]
    webhook_secret: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.provider not in VALID_PROVIDERS:
            raise ValueError(f"provider must be one of {sorted(VALID_PROVIDERS)}")


class ChannelCredentialOut(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID
    provider: str
    masked_config: Dict[str, Any]
    has_webhook_secret: bool
    health_status: str
    last_checked_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
