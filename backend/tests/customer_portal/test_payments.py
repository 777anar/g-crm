"""Tests for online payment collection (Phase 22): the Customer Portal's
first write action. POST /me/invoices/{id}/pay creates a checkout session
via the mock gateway by default; POST /me/payment-sessions/{id}/simulate is
the mock-only stand-in for a real gateway's webhook; the actual invoice
balance is only ever moved by the (reused, unchanged) RecordPaymentUseCase,
never directly by this endpoint."""
import json

import pytest


def test_create_payment_session_uses_mock_provider_by_default(app_client, portal_headers, sent_invoice):
    resp = app_client.post(
        f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}/pay", headers=portal_headers, json={}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "mock"
    assert body["status"] == "pending"
    assert body["checkout_url"].startswith("/portal/pay/")
    assert float(body["amount"]) == float(sent_invoice["total_amount"]) - float(sent_invoice["amount_paid"])


def test_cannot_pay_someone_elses_invoice(app_client, db_session, company, owner_headers, sent_invoice):
    """A second customer's portal session must not be able to start a
    checkout against the first customer's invoice."""
    from modules.crm.infrastructure.models.customer import Customer

    other = Customer(company_id=company.id, name="Other Customer", status="approved", type="individual")
    db_session.add(other)
    db_session.commit()

    access = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{other.id}/access",
        headers=owner_headers,
        json={"email": "other@portal-login.test", "password": "OtherPass123!"},
    )
    assert access.status_code == 200, access.text
    login = app_client.post(
        "/api/v1/customer_portal/auth/login",
        json={"email": "other@portal-login.test", "password": "OtherPass123!"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = app_client.post(
        f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}/pay", headers=other_headers, json={}
    )
    assert resp.status_code == 404


def test_cannot_pay_a_draft_invoice(app_client, owner_headers, portal_headers, ready_order):
    draft_invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()
    # A still-draft invoice is hidden from the portal entirely (same
    # get_invoice scoping test_get_draft_quote_404 already relies on for
    # Quotes), so the pay endpoint 404s before ever considering payability.
    resp = app_client.post(
        f"/api/v1/customer_portal/me/invoices/{draft_invoice['id']}/pay", headers=portal_headers, json={}
    )
    assert resp.status_code == 404


def test_simulate_payment_completes_invoice(app_client, portal_headers, sent_invoice):
    session = app_client.post(
        f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}/pay", headers=portal_headers, json={}
    ).json()

    resp = app_client.post(
        f"/api/v1/customer_portal/me/payment-sessions/{session['id']}/simulate",
        headers=portal_headers,
        json={"outcome": "completed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"

    invoice = app_client.get(f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}", headers=portal_headers).json()
    assert invoice["status"] == "paid"
    assert float(invoice["balance_due"]) == 0.0


def test_simulate_payment_failed_leaves_invoice_unpaid(app_client, portal_headers, sent_invoice):
    session = app_client.post(
        f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}/pay", headers=portal_headers, json={}
    ).json()

    resp = app_client.post(
        f"/api/v1/customer_portal/me/payment-sessions/{session['id']}/simulate",
        headers=portal_headers,
        json={"outcome": "failed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "failed"

    invoice = app_client.get(f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}", headers=portal_headers).json()
    assert invoice["status"] == "sent"
    assert float(invoice["amount_paid"]) == 0.0


def test_get_payment_session_status(app_client, portal_headers, sent_invoice):
    session = app_client.post(
        f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}/pay", headers=portal_headers, json={}
    ).json()
    resp = app_client.get(f"/api/v1/customer_portal/me/payment-sessions/{session['id']}", headers=portal_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == session["id"]


def test_webhook_completes_invoice_payment_and_is_idempotent(app_client, portal_headers, sent_invoice, db_session):
    from modules.finance.infrastructure.models.invoice_payment_session import InvoicePaymentSession

    session = app_client.post(
        f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}/pay", headers=portal_headers, json={}
    ).json()
    row = db_session.get(InvoicePaymentSession, session["id"])

    payload = json.dumps({"provider_session_id": row.provider_session_id, "status": "completed"}).encode("utf-8")
    resp = app_client.post(
        "/api/v1/finance/payments/webhooks/mock",
        content=payload,
        headers={"Stripe-Signature": "unused-for-mock"},
    )
    assert resp.status_code == 200, resp.text

    invoice = app_client.get(f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}", headers=portal_headers).json()
    assert invoice["status"] == "paid"

    # Idempotent: a retried webhook delivery must not double-record a payment.
    resp2 = app_client.post(
        "/api/v1/finance/payments/webhooks/mock", content=payload, headers={"Stripe-Signature": "unused-for-mock"}
    )
    assert resp2.status_code == 200, resp2.text
    invoice_after_retry = app_client.get(
        f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}", headers=portal_headers
    ).json()
    assert float(invoice_after_retry["amount_paid"]) == float(sent_invoice["total_amount"])
