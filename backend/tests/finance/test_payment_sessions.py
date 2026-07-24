"""Unit-level tests for the payment gateway provider abstraction and the use
cases directly (below the HTTP layer already covered by
tests/customer_portal/test_payments.py) -- provider-not-configured, a
signature-invalid webhook, and the invoice-creator attribution guard."""
import uuid

import pytest

from core.api.errors import ForbiddenError, ServiceUnavailableError
from core.config import settings
from modules.finance.application.dtos import CreatePaymentSessionInput
from modules.finance.application.use_cases.payment_session_use_cases import CreatePaymentSessionUseCase
from modules.finance.domain.exceptions import PaymentSessionAttributionError, PaymentSessionNotPayableError
from modules.finance.infrastructure.providers.stripe_provider import StripeProvider


def test_stripe_provider_raises_when_not_configured():
    provider = StripeProvider()
    with pytest.raises(ServiceUnavailableError):
        provider.create_checkout_session(
            provider_session_reference="ref",
            amount=100,
            currency="AZN",
            description="Invoice X",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )


def test_stripe_provider_rejects_invalid_webhook_signature(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    provider = StripeProvider()
    with pytest.raises(ForbiddenError):
        provider.parse_webhook_event(raw_body=b'{"type": "checkout.session.completed"}', signature_header="bad-signature")


def test_create_payment_session_rejects_fully_paid_invoice(app_client, owner_headers, sent_invoice, db_session):
    pay_resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": sent_invoice["total_amount"], "method": "cash"},
    )
    assert pay_resp.status_code == 200, pay_resp.text

    from modules.finance.infrastructure.models.invoice import Invoice

    invoice_row = db_session.get(Invoice, uuid.UUID(sent_invoice["id"]))
    with pytest.raises(PaymentSessionNotPayableError):
        CreatePaymentSessionUseCase(db_session).execute(
            CreatePaymentSessionInput(
                company_id=invoice_row.company_id,
                customer_id=invoice_row.customer_id,
                invoice_id=invoice_row.id,
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )
        )


def test_create_payment_session_requires_invoice_creator(app_client, owner_headers, sent_invoice, db_session):
    from modules.finance.infrastructure.models.invoice import Invoice

    invoice_row = db_session.get(Invoice, uuid.UUID(sent_invoice["id"]))
    invoice_row.created_by = None
    db_session.commit()

    with pytest.raises(PaymentSessionAttributionError):
        CreatePaymentSessionUseCase(db_session).execute(
            CreatePaymentSessionInput(
                company_id=invoice_row.company_id,
                customer_id=invoice_row.customer_id,
                invoice_id=invoice_row.id,
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )
        )
