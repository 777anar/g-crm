"""The provider seam every real e-signature integration will implement.

E-signature is genuinely cross-cutting (Sales' measurement sign-off and
Installation's job completion sign-off both need "send a document out for a
tamper-evident signature, get notified when it's signed back"), so it lives
in core exactly like `core/storage` -- a generic capability with no business
meaning of its own, used by whichever module needs it, the same way
`core/storage/client.py` is a shared client any module calls directly rather
than each module reimplementing file storage. This is deliberately NOT the
`AIProvider`/`ChannelProvider` pattern (a provider abstraction owned by the
one module that uses it) because, uniquely among this codebase's three
provider abstractions, two independent modules need the same integration.

No use case ever imports a concrete provider directly -- it always resolves
one through `registry.get_esignature_provider()`. Plugging in a different
real integration later is a change to this library only.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Status values a provider's webhook event or send result can report --
# shared vocabulary every calling module maps onto its own tracking columns.
ESIGNATURE_STATUS_SENT = "sent"
ESIGNATURE_STATUS_COMPLETED = "completed"
ESIGNATURE_STATUS_DECLINED = "declined"
# A real provider's webhook fires for events callers don't act on yet (e.g.
# "viewed", an intermediate signer completed in a multi-signer flow) --
# reported as "other" so a caller can safely ignore it rather than the
# provider having to guess which events matter to which caller.
ESIGNATURE_STATUS_OTHER = "other"


@dataclass
class ESignatureSendResult:
    provider_request_id: str
    status: str = ESIGNATURE_STATUS_SENT


@dataclass
class ESignatureWebhookEvent:
    provider_request_id: str
    status: str


class ESignatureProvider(ABC):
    #: Short machine name, e.g. "mock" or "dropbox_sign" -- stored on every
    #: signature request record this provider produces.
    name: str

    @abstractmethod
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
        """Sends `document_bytes` out for signature to one signer. Returns
        the provider's own request id (used to correlate a later webhook
        callback back to whichever row the calling module tracks it as)."""
        raise NotImplementedError

    @abstractmethod
    def verify_and_parse_webhook(self, *, payload: str) -> ESignatureWebhookEvent:
        """`payload` is the raw JSON string posted in the callback's `json`
        form field (Dropbox Sign's own webhook shape; the mock provider's
        "simulate" call from our own frontend uses the same field name so
        every caller's webhook endpoint has one code path regardless of
        provider). Verifies the callback genuinely came from this provider
        (raising `core.api.errors.ForbiddenError` if not) and maps its event
        shape onto the shared status vocabulary above."""
        raise NotImplementedError

    @abstractmethod
    def download_signed_document(self, *, provider_request_id: str) -> bytes:
        """Fetches the final signed document once a webhook reports
        `ESIGNATURE_STATUS_COMPLETED`, so the calling module can store it as
        a `core.storage.models.Document` the same way any other upload is
        stored."""
        raise NotImplementedError
