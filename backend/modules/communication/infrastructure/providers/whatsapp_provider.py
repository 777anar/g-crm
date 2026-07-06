"""WhatsApp Business Cloud API, via the Meta Graph API.

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages

Outbound media: the ChannelProvider.send() shape (channel, external_contact_id,
body, message_type) is fixed and unchanged for Version 2.9 -- so for
message_type in {image, document, audio, video}, `body` is treated as the
media's URL (already uploaded via the core Documents pipeline, exactly like
every inbound attachment already is), not as caption text. This keeps
"the provider abstraction must remain unchanged" literally true while still
supporting real media sends.
"""
from typing import Any, Dict

from modules.communication.domain.exceptions import ProviderConfigurationError
from modules.communication.infrastructure.providers.base import ChannelProvider
from modules.communication.infrastructure.providers.meta_client import MetaGraphClient

_MEDIA_TYPES = {"image", "document", "audio", "video"}

REQUIRED_CONFIG_FIELDS = ("phone_number_id", "access_token", "app_secret", "verify_token")


class MetaWhatsAppProvider(ChannelProvider):
    def __init__(self, config: Dict[str, Any]):
        missing = [f for f in REQUIRED_CONFIG_FIELDS if not config.get(f)]
        if missing:
            raise ProviderConfigurationError(f"WhatsApp config missing required field(s): {', '.join(missing)}")
        self.config = config
        self.phone_number_id = config["phone_number_id"]
        self.client = MetaGraphClient(access_token=config["access_token"], api_version=config.get("api_version"))

    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": external_contact_id,
        }
        if message_type in _MEDIA_TYPES:
            payload["type"] = message_type
            payload[message_type] = {"link": body}
        else:
            payload["type"] = "text"
            payload["text"] = {"body": body}

        result = self.client.post(f"{self.phone_number_id}/messages", payload)
        messages = result.get("messages") or []
        if messages:
            return messages[0].get("id", "")
        return ""

    def test_connection(self) -> Dict[str, Any]:
        result = self.client.get(self.phone_number_id, params={"fields": "verified_name,display_phone_number"})
        return {"ok": True, "detail": f"Connected as {result.get('display_phone_number', self.phone_number_id)}"}
