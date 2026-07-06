"""Tests for the Finance module's payment recording."""


def test_cannot_pay_draft_invoice(app_client, owner_headers, ready_order):
    invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/finance/invoices/{invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "100.00", "method": "cash"},
    )
    assert resp.status_code == 422, resp.text


def test_partial_payment_moves_invoice_to_partially_paid(app_client, owner_headers, sent_invoice):
    resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "200.00", "method": "cash"},
    )
    assert resp.status_code == 200, resp.text

    invoice = app_client.get(f"/api/v1/finance/invoices/{sent_invoice['id']}", headers=owner_headers).json()
    assert invoice["status"] == "partially_paid"
    assert invoice["amount_paid"] == "200.00"
    assert invoice["balance_due"] == "242.50"


def test_full_payment_moves_invoice_to_paid(app_client, owner_headers, sent_invoice):
    resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "442.50", "method": "bank_transfer"},
    )
    assert resp.status_code == 200, resp.text

    invoice = app_client.get(f"/api/v1/finance/invoices/{sent_invoice['id']}", headers=owner_headers).json()
    assert invoice["status"] == "paid"
    assert invoice["paid_at"] is not None
    assert invoice["balance_due"] == "0.00"


def test_two_partial_payments_complete_invoice(app_client, owner_headers, sent_invoice):
    app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "200.00", "method": "cash"},
    )
    resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "242.50", "method": "card"},
    )
    assert resp.status_code == 200, resp.text

    invoice = app_client.get(f"/api/v1/finance/invoices/{sent_invoice['id']}", headers=owner_headers).json()
    assert invoice["status"] == "paid"

    payments = app_client.get(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments", headers=owner_headers
    ).json()["items"]
    assert len(payments) == 2


def test_overpayment_rejected(app_client, owner_headers, sent_invoice):
    resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "500.00", "method": "cash"},
    )
    assert resp.status_code == 422, resp.text


def test_zero_amount_payment_rejected(app_client, owner_headers, sent_invoice):
    resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "0.00", "method": "cash"},
    )
    assert resp.status_code == 422, resp.text


def test_invalid_payment_method_rejected(app_client, owner_headers, sent_invoice):
    resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "100.00", "method": "crypto"},
    )
    assert resp.status_code == 400, resp.text


def test_cannot_pay_cancelled_invoice(app_client, owner_headers, sent_invoice):
    app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/status",
        headers=owner_headers,
        json={"status": "cancelled"},
    )

    resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "100.00", "method": "cash"},
    )
    assert resp.status_code == 422, resp.text
