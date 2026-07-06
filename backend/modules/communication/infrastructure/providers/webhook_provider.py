"""Generic outbound webhook provider -- lets any external system (an
internal tool, a partner's own chat platform, a bespoke automation) be a
Communication Center channel without this codebase needing to know its
specific API shape. Outbound: POSTs a normalized JSON envelope to a
configured URL, HMAC-signed the same way our own inbound webhook endpoint
verifies signatures, so the receiving system can authenticate us too.
"""
import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, Optional

import httpx

from modules.communication.domain.exceptions import ProviderConfigurationError, ProviderRequestError
from modules.communication.infrastructure.providers.base import ChannelProvider

REQUIRED_CONFIG_FIELDS = ("outbound_url", "secret")


def sign_webhook_payload(*, secret: str, raw_body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def verify_webhook_signature(*, secret: str, raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Accepts the header either bare (`<hex>`) or prefixed (`sha256=<hex>`,
    matching what GenericWebhookProvider.send() sends outbound and how
    Meta's own X-Hub-Signature-256 is formatted) -- our documented inbound
    contract for this provider allows either."""
    if not signature_header:
        return False
    provided = signature_header.split("=", 1)[1] if signature_header.startswith("sha256=") else signature_header
    expected = sign_webhook_payload(secret=secret, raw_body=raw_body)
    return hmac.compare_digest(expected, provided)


class GenericWebhookProvider(ChannelProvider):
    def __init__(self, config: Dict[str, Any]):
        missing = [f for f in REQUIRED_CONFIG_FIELDS if not config.get(f)]
        if missing:
            raise ProviderConfigurationError(f"Webhook config missing required field(s): {', '.join(missing)}")
        self.config = config

    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        message_id = f"webhook-{uuid.uuid4()}"
        envelope = {
            "event": "message.outbound",
            "message_id": message_id,
            "channel_id": str(getattr(channel, "id", "")),
            "to": external_contact_id,
            "body": body,
            "message_type": message_type,
            "sent_at": time.time(),
        }
        raw_body = json.dumps(envelope, sort_keys=True).encode("utf-8")
        signature = sign_webhook_payload(secret=self.config["secret"], raw_body=raw_body)
        headers = {"Content-Type": "application/json", "X-Signature-256": f"sha256={signature}"}
        headers.update(self.config.get("headers") or {})

        with httpx.Client(timeout=15.0) as client:
            response = client.post(self.config["outbound_url"], content=raw_body, headers=headers)
        if response.status_code >= 400:
            raise ProviderRequestError(f"Webhook endpoint returned {response.status_code}: {response.text}")
        return message_id

    def test_connection(self) -> Dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            response = client.request("HEAD", self.config["outbound_url"])
        if response.status_code >= 500:
            raise ProviderRequestError(f"Webhook endpoint returned {response.status_code}")
        return {"ok": True, "detail": f"Reached {self.config['outbound_url']} ({response.status_code})"}
