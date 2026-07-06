"""Thin, shared HTTP helper for the three Meta Graph API-backed providers
(WhatsApp Business Cloud API, Instagram Messaging API, Messenger Send API).
All three authenticate the same way (bearer token in the Authorization
header) and share the same base URL shape, error envelope, and rate-limit
signaling -- this file is where that commonality lives instead of being
copy-pasted three times.
"""
import hashlib
import hmac
from typing import Any, Dict, Optional

import httpx

from modules.communication.domain.exceptions import ProviderAuthError, ProviderRateLimitedError, ProviderRequestError


def verify_meta_signature(*, app_secret: str, raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Verifies Meta's `X-Hub-Signature-256` header: `sha256=<hex hmac>` of
    the raw request body, keyed by the app secret. Meta's own documented
    scheme -- https://developers.facebook.com/docs/graph-api/webhooks/getting-started#validate-payloads
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)

DEFAULT_GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = "https://graph.facebook.com"


class MetaGraphClient:
    def __init__(self, *, access_token: str, api_version: Optional[str] = None, timeout: float = 15.0):
        self.access_token = access_token
        self.api_version = api_version or DEFAULT_GRAPH_API_VERSION
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{GRAPH_API_BASE}/{self.api_version}/{path.lstrip('/')}"

    def post(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self._url(path),
                json=json_body,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        return self._handle_response(response)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                self._url(path),
                params=params or {},
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: httpx.Response) -> Dict[str, Any]:
        if response.status_code == 429:
            raise ProviderRateLimitedError("Meta Graph API rate limit reached")
        if response.status_code in (401, 403):
            raise ProviderAuthError(f"Meta Graph API rejected credentials: {response.text}")
        if response.status_code >= 400:
            raise ProviderRequestError(f"Meta Graph API error {response.status_code}: {response.text}")
        return response.json()
