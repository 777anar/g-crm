"""The provider seam the real payment gateway (Stripe) implements, mirroring
`modules/ai/infrastructure/providers/base.py`'s `AIProvider` and
`modules/communication/.../providers/base.py`'s `ChannelProvider`: no use
case ever imports a concrete provider directly, always resolving one through
`registry.get_payment_gateway_provider()`.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

PAYMENT_SESSION_STATUS_COMPLETED = "completed"
PAYMENT_SESSION_STATUS_FAILED = "failed"
# A real gateway's webhook fires for events this integration doesn't act on
# (e.g. a Checkout Session merely expiring unpaid) -- reported as "other" so
# a caller can safely ignore it.
PAYMENT_SESSION_STATUS_OTHER = "other"


@dataclass
class CheckoutSessionResult:
    provider_session_id: str
    checkout_url: str


@dataclass
class PaymentWebhookEvent:
    provider_session_id: str
    status: str


class PaymentGatewayProvider(ABC):
    #: Short machine name, e.g. "mock" or "stripe" -- stored on every
    #: InvoicePaymentSession this provider produces.
    name: str

    @abstractmethod
    def create_checkout_session(
        self,
        *,
        provider_session_reference: str,
        amount: Decimal,
        currency: str,
        description: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult:
        """Starts a hosted checkout for one invoice's outstanding balance.
        `provider_session_reference` is an idempotency key / metadata tag
        (the InvoicePaymentSession row's own id, generated before the
        provider call) so a webhook event can always be correlated back to
        our own row even before the provider's own session id is known."""
        raise NotImplementedError

    @abstractmethod
    def parse_webhook_event(self, *, raw_body: bytes, signature_header: str) -> PaymentWebhookEvent:
        """Verifies the callback's signature (raising
        `core.api.errors.ForbiddenError` if invalid) and maps it onto the
        shared status vocabulary above."""
        raise NotImplementedError
