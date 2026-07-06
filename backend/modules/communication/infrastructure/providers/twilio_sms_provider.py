"""Twilio SMS, via Twilio's REST API.
Reference: https://www.twilio.com/docs/sms/api/message-resource
"""
import base64
import hashlib
import hmac
from typing import Any, Dict, Optional

import httpx

from modules.communication.domain.exceptions import (
    ProviderAuthError,
    ProviderConfigurationError,
    ProviderRateLimitedError,
    ProviderRequestError,
)
from modules.communication.infrastructure.providers.base import ChannelProvider

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
REQUIRED_CONFIG_FIELDS = ("account_sid", "auth_token", "from_number")


class TwilioSMSProvider(ChannelProvider):
    def __init__(self, config: Dict[str, Any]):
        missing = [f for f in REQUIRED_CONFIG_FIELDS if not config.get(f)]
        if missing:
            raise ProviderConfigurationError(f"Twilio config missing required field(s): {', '.join(missing)}")
        self.config = config
        self.account_sid = config["account_sid"]
        self.auth_token = config["auth_token"]

    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        # Media types are sent as MMS via Twilio's MediaUrl parameter -- body
        # is the already-uploaded media URL, same URL-reference convention
        # used by the Meta providers and SMTP.
        form: Dict[str, str] = {
            "From": self.config["from_number"],
            "To": external_contact_id,
        }
        if message_type in {"image", "document", "audio", "video"}:
            form["MediaUrl"] = body
            form["Body"] = self.config.get("default_caption", "")
        else:
            form["Body"] = body

        url = f"{TWILIO_API_BASE}/Accounts/{self.account_sid}/Messages.json"
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, data=form, auth=(self.account_sid, self.auth_token))
        return self._handle_response(response).get("sid", "")

    def test_connection(self) -> Dict[str, Any]:
        url = f"{TWILIO_API_BASE}/Accounts/{self.account_sid}.json"
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, auth=(self.account_sid, self.auth_token))
        result = self._handle_response(response)
        return {"ok": True, "detail": f"Connected to Twilio account '{result.get('friendly_name', self.account_sid)}'"}

    @staticmethod
    def _handle_response(response: httpx.Response) -> Dict[str, Any]:
        if response.status_code == 429:
            raise ProviderRateLimitedError("Twilio rate limit reached")
        if response.status_code in (401, 403):
            raise ProviderAuthError(f"Twilio rejected credentials: {response.text}")
        if response.status_code >= 400:
            raise ProviderRequestError(f"Twilio error {response.status_code}: {response.text}")
        return response.json()


def verify_twilio_signature(*, auth_token: str, url: str, form_params: Dict[str, str], signature_header: Optional[str]) -> bool:
    """Verifies Twilio's `X-Twilio-Signature` header: base64(HMAC-SHA1(auth_token,
    url + sorted-concatenated-form-params)). Twilio's own documented scheme --
    https://www.twilio.com/docs/usage/webhooks/webhooks-security
    """
    if not signature_header:
        return False
    data = url
    for key in sorted(form_params.keys()):
        data += key + form_params[key]
    expected = base64.b64encode(hmac.new(auth_token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(expected, signature_header)
