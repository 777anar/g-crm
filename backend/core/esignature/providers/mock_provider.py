"""Deterministic mock -- the default e-signature provider, requiring no
credentials, so every environment (dev, CI, a company that hasn't signed up
with a real e-signature vendor yet) has a fully working signing flow.
Nothing is actually sent anywhere: `send_for_signature` mints a random
request id, and completion is driven by our own frontend posting the same
`json` field shape a real webhook would (see `verify_and_parse_webhook`),
so the calling module's webhook endpoint has exactly one code path for both
providers."""
import json
import uuid

from core.esignature.providers.base import (
    ESIGNATURE_STATUS_COMPLETED,
    ESIGNATURE_STATUS_DECLINED,
    ESIGNATURE_STATUS_SENT,
    ESignatureProvider,
    ESignatureSendResult,
    ESignatureWebhookEvent,
)

_VALID_SIMULATED_STATUSES = {ESIGNATURE_STATUS_COMPLETED, ESIGNATURE_STATUS_DECLINED}


class MockESignatureProvider(ESignatureProvider):
    name = "mock"

    def send_for_signature(
        self,
        *,
        document_bytes: bytes,
        document_name: str,
        title: str,
        message: str,
        signer_name: str,
        signer_email: str,
    ) -> ESignatureSendResult:
        return ESignatureSendResult(provider_request_id=f"mock-{uuid.uuid4().hex}", status=ESIGNATURE_STATUS_SENT)

    def verify_and_parse_webhook(self, *, payload: str) -> ESignatureWebhookEvent:
        data = json.loads(payload)
        status = data["status"]
        if status not in _VALID_SIMULATED_STATUSES:
            status = ESIGNATURE_STATUS_COMPLETED
        return ESignatureWebhookEvent(provider_request_id=data["provider_request_id"], status=status)

    def download_signed_document(self, *, provider_request_id: str) -> bytes:
        return f"Mock signed document for request {provider_request_id}".encode("utf-8")
