"""Tests for the Finance module's invoice lifecycle."""


def test_create_invoice_requires_ready_order(app_client, owner_headers, accepted_quote):
    order = app_client.post(
        "/api/v1/orders", headers=owner_headers, json={"quote_id": str(accepted_quote.id)}
    ).json()

    resp = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": order["id"]}
    )
    assert resp.status_code == 422, resp.text


def test_create_invoice_success_snapshots_order_items(app_client, owner_headers, ready_order):
    resp = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["invoice_number"].startswith("INV-")
    assert body["order_id"] == ready_order["id"]
    assert body["total_amount"] == ready_order["total_final"]
    assert body["amount_paid"] == "0.00"
    assert body["balance_due"] == ready_order["total_final"]

    lines = app_client.get(f"/api/v1/finance/invoices/{body['id']}/lines", headers=owner_headers).json()["items"]
    assert len(lines) == 1
    assert lines[0]["description"] == "Marble countertop"
    assert lines[0]["amount"] == "375.00"


def test_create_invoice_twice_returns_422(app_client, owner_headers, ready_order):
    first = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    )
    assert first.status_code == 200, first.text

    second = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    )
    assert second.status_code == 422, second.text


def test_send_invoice(app_client, owner_headers, ready_order):
    invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/finance/invoices/{invoice['id']}/status", headers=owner_headers, json={"status": "sent"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sent"
    assert body["sent_at"] is not None


def test_cannot_manually_set_paid_status(app_client, owner_headers, sent_invoice):
    """paid/partially_paid may only ever result from RecordPaymentUseCase --
    the manual status endpoint must refuse them even though they're
    structurally reachable from 'sent' in the transition graph."""
    resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/status",
        headers=owner_headers,
        json={"status": "paid"},
    )
    assert resp.status_code == 422, resp.text


def test_invalid_invoice_transition_returns_422(app_client, owner_headers, ready_order):
    invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/finance/invoices/{invoice['id']}/status",
        headers=owner_headers,
        json={"status": "overdue"},
    )
    assert resp.status_code == 422, resp.text


def test_cancel_invoice(app_client, owner_headers, ready_order):
    invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/finance/invoices/{invoice['id']}/status",
        headers=owner_headers,
        json={"status": "cancelled", "cancelled_reason": "Order cancelled by customer"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "cancelled"
    assert body["cancelled_reason"] == "Order cancelled by customer"


def test_cannot_edit_cancelled_invoice(app_client, owner_headers, ready_order):
    invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()
    app_client.post(
        f"/api/v1/finance/invoices/{invoice['id']}/status",
        headers=owner_headers,
        json={"status": "cancelled"},
    )

    resp = app_client.patch(
        f"/api/v1/finance/invoices/{invoice['id']}", headers=owner_headers, json={"notes": "too late"}
    )
    assert resp.status_code == 422, resp.text


def test_update_invoice_notes_and_due_date(app_client, owner_headers, ready_order):
    invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    resp = app_client.patch(
        f"/api/v1/finance/invoices/{invoice['id']}",
        headers=owner_headers,
        json={"due_date": "2026-08-15", "notes": "Net 30"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["due_date"] == "2026-08-15"
    assert body["notes"] == "Net 30"


def test_list_and_get_by_order(app_client, owner_headers, ready_order):
    created = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    list_resp = app_client.get("/api/v1/finance/invoices", headers=owner_headers)
    assert list_resp.status_code == 200
    assert any(i["id"] == created["id"] for i in list_resp.json()["items"])

    by_order_resp = app_client.get(
        f"/api/v1/finance/invoices/by-order/{ready_order['id']}", headers=owner_headers
    )
    assert by_order_resp.status_code == 200
    assert by_order_resp.json()["id"] == created["id"]


def test_get_invoice_for_order_without_invoice_returns_404(app_client, owner_headers, ready_order):
    resp = app_client.get(
        f"/api/v1/finance/invoices/by-order/{ready_order['id']}", headers=owner_headers
    )
    assert resp.status_code == 404
