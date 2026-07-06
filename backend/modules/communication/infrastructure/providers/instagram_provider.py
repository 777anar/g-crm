"""Instagram Messaging API, via the Meta Graph API. Shares the Messenger
Send API's request shape (recipient/message) but is scoped to the
Instagram-scoped user id and the IG professional account, per:
https://developers.facebook.com/docs/messenger-platform/instagram
"""
from typing import Any, Dict

from modules.communication.domain.exceptions import ProviderConfigurationError
from modules.communication.infrastructure.providers.base import ChannelProvider
from modules.communication.infrastructure.providers.meta_client import MetaGraphClient

_MEDIA_TYPES = {"image", "document", "audio", "video"}

REQUIRED_CONFIG_FIELDS = ("ig_user_id", "access_token", "app_secret", "verify_token")


class MetaInstagramProvider(ChannelProvider):
    def __init__(self, config: Dict[str, Any]):
        missing = [f for f in REQUIRED_CONFIG_FIELDS if not config.get(f)]
        if missing:
            raise ProviderConfigurationError(f"Instagram config missing required field(s): {', '.join(missing)}")
        self.config = config
        self.ig_user_id = config["ig_user_id"]
        self.client = MetaGraphClient(access_token=config["access_token"], api_version=config.get("api_version"))

    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        message: Dict[str, Any]
        if message_type in _MEDIA_TYPES:
            message = {"attachment": {"type": "image" if message_type == "image" else "file", "payload": {"url": body}}}
        else:
            message = {"text": body}

        payload = {"recipient": {"id": external_contact_id}, "message": message}
        result = self.client.post(f"{self.ig_user_id}/messages", payload)
        return result.get("message_id", "")

    def test_connection(self) -> Dict[str, Any]:
        result = self.client.get(self.ig_user_id, params={"fields": "username"})
        return {"ok": True, "detail": f"Connected as @{result.get('username', self.ig_user_id)}"}
