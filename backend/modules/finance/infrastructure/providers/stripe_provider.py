"""The first real `PaymentGatewayProvider` implementation (Phase 22: Online
payment collection), behind the exact same interface `MockPaymentGatewayProvider`
implements -- no use case, DTO, schema, or frontend change needed to add this
class, the same non-goal discipline Phase 21 held for `AnthropicProvider`.

Uses Stripe Checkout (hosted payment page) rather than building a custom
card form: the customer is redirected to a Stripe-hosted URL and back, and
completion is confirmed asynchronously via the `checkout.session.completed`
webhook -- never trusted from the browser redirect alone, since a customer
closing the tab after paying but before the redirect fires would otherwise
leave the invoice looking unpaid, and a customer replaying/forging the
redirect URL would otherwise be able to fake a completed payment.
"""
from decimal import Decimal

import stripe

from core.api.errors import ForbiddenError, ServiceUnavailableError
from core.config import settings
from modules.finance.infrastructure.providers.base import (
    PAYMENT_SESSION_STATUS_COMPLETED,
    PAYMENT_SESSION_STATUS_FAILED,
    PAYMENT_SESSION_STATUS_OTHER,
    CheckoutSessionResult,
    PaymentGatewayProvider,
    PaymentWebhookEvent,
)

_EVENT_TYPE_TO_STATUS = {
    "checkout.session.completed": PAYMENT_SESSION_STATUS_COMPLETED,
    "checkout.session.expired": PAYMENT_SESSION_STATUS_FAILED,
    "checkout.session.async_payment_failed": PAYMENT_SESSION_STATUS_FAILED,
}


class StripeProvider(PaymentGatewayProvider):
    name = "stripe"

    def _get_client(self) -> stripe.StripeClient:
        if not settings.stripe_secret_key:
            raise ServiceUnavailableError(
                "The 'stripe' payment gateway is registered but STRIPE_SECRET_KEY is not configured -- "
                "set it in the environment to enable real payment collection, or use provider 'mock' until then."
            )
        return stripe.StripeClient(api_key=settings.stripe_secret_key)

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
        client = self._get_client()
        try:
            session = client.v1.checkout.sessions.create(
                params={
                    "mode": "payment",
                    "client_reference_id": provider_session_reference,
                    "metadata": {"provider_session_reference": provider_session_reference},
                    "line_items": [
                        {
                            "price_data": {
                                "currency": currency.lower(),
                                "product_data": {"name": description},
                                # Stripe amounts are the smallest currency unit
                                # (cents/qəpik) -- AZN, like USD, has 2 decimals.
                                "unit_amount": int((amount * 100).to_integral_value()),
                            },
                            "quantity": 1,
                        }
                    ],
                    "success_url": success_url,
                    "cancel_url": cancel_url,
                }
            )
        except stripe.AuthenticationError as exc:
            raise ServiceUnavailableError("Stripe rejected the configured secret key (authentication failed).") from exc
        except stripe.APIConnectionError as exc:
            raise ServiceUnavailableError("Could not reach the Stripe API.") from exc
        except stripe.StripeError as exc:
            raise ServiceUnavailableError(f"Stripe API error: {exc.user_message or str(exc)}") from exc

        return CheckoutSessionResult(provider_session_id=session.id, checkout_url=session.url)

    def parse_webhook_event(self, *, raw_body: bytes, signature_header: str) -> PaymentWebhookEvent:
        if not settings.stripe_webhook_secret:
            raise ServiceUnavailableError("STRIPE_WEBHOOK_SECRET is not configured -- cannot verify Stripe webhooks.")
        try:
            event = stripe.Webhook.construct_event(raw_body, signature_header, settings.stripe_webhook_secret)
        except (stripe.SignatureVerificationError, ValueError) as exc:
            raise ForbiddenError("Stripe webhook signature verification failed") from exc

        status = _EVENT_TYPE_TO_STATUS.get(event["type"], PAYMENT_SESSION_STATUS_OTHER)
        provider_session_id = event["data"]["object"]["id"]
        return PaymentWebhookEvent(provider_session_id=provider_session_id, status=status)
