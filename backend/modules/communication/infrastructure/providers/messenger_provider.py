"""Facebook Messenger Platform Send API, via the Meta Graph API.

Reference: https://developers.facebook.com/docs/messenger-platform/reference/send-api
"""
from typing import Any, Dict

from modules.communication.domain.exceptions import ProviderConfigurationError
from modules.communication.infrastructure.providers.base import ChannelProvider
from modules.communication.infrastructure.providers.meta_client import MetaGraphClient

_MEDIA_TYPES = {"image", "document", "audio", "video"}
_ATTACHMENT_TYPE_MAP = {"image": "image", "document": "file", "audio": "audio", "video": "video"}

REQUIRED_CONFIG_FIELDS = ("page_id", "page_access_token", "app_secret", "verify_token")


class MetaMessengerProvider(ChannelProvider):
    def __init__(self, config: Dict[str, Any]):
        missing = [f for f in REQUIRED_CONFIG_FIELDS if not config.get(f)]
        if missing:
            raise ProviderConfigurationError(f"Messenger config missing required field(s): {', '.join(missing)}")
        self.config = config
        self.page_id = config["page_id"]
        self.client = MetaGraphClient(access_token=config["page_access_token"], api_version=config.get("api_version"))

    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        message: Dict[str, Any]
        if message_type in _MEDIA_TYPES:
            message = {
                "attachment": {
                    "type": _ATTACHMENT_TYPE_MAP[message_type],
                    "payload": {"url": body, "is_reusable": True},
                }
            }
        else:
            message = {"text": body}

        payload = {
            "recipient": {"id": external_contact_id},
            "messaging_type": "RESPONSE",
            "message": message,
        }
        result = self.client.post(f"{self.page_id}/messages", payload)
        return result.get("message_id", "")

    def test_connection(self) -> Dict[str, Any]:
        result = self.client.get(self.page_id, params={"fields": "name"})
        return {"ok": True, "detail": f"Connected to Page '{result.get('name', self.page_id)}'"}
