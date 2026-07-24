"""The first real `ESignatureProvider` implementation: Dropbox Sign
(formerly HelloSign) API v3, via the official `dropbox_sign` SDK. Uses the
plain hosted signing flow (`signature_request_send`) -- the signer gets an
emailed link and signs on Dropbox Sign's own page -- rather than embedded
signing, which would need an OAuth API App `client_id` and a frontend JS SDK
just to render an iframe. A hosted link is a complete, real, verifiable
e-signature integration on its own, and it keeps this integration entirely
backend-driven, matching how `AnthropicProvider`/`StripeProvider` need no
frontend SDK either.

Authentication is HTTP Basic with the API key as the username (Dropbox
Sign's own convention -- see `Configuration.auth_settings`), and webhook
verification is an HMAC-SHA256 of `event_time + event_type` keyed by the
same API key (`EventCallbackHelper.is_valid`), not a header signature --
both handled by the SDK, not reimplemented here.
"""
import io

import dropbox_sign as ds
from dropbox_sign.rest import ApiException as DropboxSignApiException

from core.api.errors import ForbiddenError, ServiceUnavailableError
from core.config import settings
from core.esignature.providers.base import (
    ESIGNATURE_STATUS_COMPLETED,
    ESIGNATURE_STATUS_DECLINED,
    ESIGNATURE_STATUS_OTHER,
    ESignatureProvider,
    ESignatureSendResult,
    ESignatureWebhookEvent,
)

_EVENT_TYPE_TO_STATUS = {
    "signature_request_all_signed": ESIGNATURE_STATUS_COMPLETED,
    "signature_request_signed": ESIGNATURE_STATUS_COMPLETED,
    "signature_request_declined": ESIGNATURE_STATUS_DECLINED,
}


class DropboxSignProvider(ESignatureProvider):
    name = "dropbox_sign"

    def _get_api_client(self) -> ds.ApiClient:
        if not settings.esignature_api_key:
            raise ServiceUnavailableError(
                "The 'dropbox_sign' e-signature provider is registered but ESIGNATURE_API_KEY is not "
                "configured -- set it in the environment to enable real e-signature requests, or use "
                "provider 'mock' until then."
            )
        configuration = ds.Configuration(username=settings.esignature_api_key)
        return ds.ApiClient(configuration)

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
        with self._get_api_client() as api_client:
            api = ds.SignatureRequestApi(api_client)
            request = ds.SignatureRequestSendRequest(
                title=title,
                subject=title,
                message=message,
                signers=[ds.SubSignatureRequestSigner(name=signer_name, email_address=signer_email)],
                files=[io.BytesIO(document_bytes)],
                test_mode=settings.environment != "production",
            )
            try:
                response = api.signature_request_send(request)
            except DropboxSignApiException as exc:
                raise ServiceUnavailableError(f"Dropbox Sign API error: {exc}") from exc
        return ESignatureSendResult(provider_request_id=response.signature_request.signature_request_id)

    def verify_and_parse_webhook(self, *, payload: str) -> ESignatureWebhookEvent:
        import json

        event_callback = ds.EventCallbackRequest(**json.loads(payload))
        if not ds.EventCallbackHelper.is_valid(settings.esignature_api_key, event_callback):
            raise ForbiddenError("Dropbox Sign webhook signature verification failed")

        event_type = event_callback.event.event_type
        status = _EVENT_TYPE_TO_STATUS.get(event_type, ESIGNATURE_STATUS_OTHER)
        provider_request_id = event_callback.signature_request.signature_request_id
        return ESignatureWebhookEvent(provider_request_id=provider_request_id, status=status)

    def download_signed_document(self, *, provider_request_id: str) -> bytes:
        with self._get_api_client() as api_client:
            api = ds.SignatureRequestApi(api_client)
            try:
                file_obj = api.signature_request_files(provider_request_id, file_type="pdf")
            except DropboxSignApiException as exc:
                raise ServiceUnavailableError(f"Dropbox Sign API error: {exc}") from exc
            return file_obj.read()
