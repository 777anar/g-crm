"""Deterministic mock -- the default payment gateway, requiring no
credentials. `checkout_url` points back into our own Customer Portal (a
relative path, not an external host) where a "Simulate payment" page posts
the same webhook shape a real gateway would (see
`ai`/`esignature`'s identical mock-drives-its-own-webhook-shape convention),
so `HandlePaymentWebhookUseCase` has exactly one code path regardless of
provider."""
import json
import uuid

from modules.finance.infrastructure.providers.base import (
    PAYMENT_SESSION_STATUS_COMPLETED,
    PAYMENT_SESSION_STATUS_FAILED,
    CheckoutSessionResult,
    PaymentGatewayProvider,
    PaymentWebhookEvent,
)

_VALID_SIMULATED_STATUSES = {PAYMENT_SESSION_STATUS_COMPLETED, PAYMENT_SESSION_STATUS_FAILED}


class MockPaymentGatewayProvider(PaymentGatewayProvider):
    name = "mock"

    def create_checkout_session(
        self, *, provider_session_reference, amount, currency, description, success_url, cancel_url
    ) -> CheckoutSessionResult:
        provider_session_id = f"mock_{uuid.uuid4().hex}"
        return CheckoutSessionResult(
            provider_session_id=provider_session_id,
            checkout_url=f"/portal/pay/{provider_session_id}",
        )

    def parse_webhook_event(self, *, raw_body: bytes, signature_header: str) -> PaymentWebhookEvent:
        data = json.loads(raw_body)
        status = data["status"]
        if status not in _VALID_SIMULATED_STATUSES:
            status = PAYMENT_SESSION_STATUS_COMPLETED
        return PaymentWebhookEvent(provider_session_id=data["provider_session_id"], status=status)
