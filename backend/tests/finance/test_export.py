"""Tests for accounting/ERP export (Phase 22): CSV exports of Invoices,
Payments, Expenses, and a synthesized double-entry-style Journal, so Finance
data doesn't require manual re-entry into an external accounting system."""
import csv
import io


def _rows(response):
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))


def test_export_invoices_csv(app_client, owner_headers, sent_invoice):
    resp = app_client.get("/api/v1/finance/export/invoices", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    rows = _rows(resp)
    assert rows[0] == ["invoice_number", "issue_date", "due_date", "status", "currency", "subtotal_amount", "total_amount", "amount_paid"]
    assert any(r[0] == sent_invoice["invoice_number"] for r in rows[1:])


def test_export_payments_csv(app_client, owner_headers, sent_invoice):
    pay_resp = app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "100.00", "method": "cash"},
    )
    assert pay_resp.status_code == 200, pay_resp.text

    resp = app_client.get("/api/v1/finance/export/payments", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    rows = _rows(resp)
    assert rows[0] == ["invoice_number", "paid_at", "method", "amount", "reference_note"]
    assert any(r[0] == sent_invoice["invoice_number"] and r[2] == "cash" for r in rows[1:])


def test_export_expenses_csv(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "materials", "amount": "250.00", "expense_date": "2026-07-01", "description": "Slab delivery"},
    )
    assert resp.status_code == 200, resp.text

    export_resp = app_client.get("/api/v1/finance/export/expenses", headers=owner_headers)
    assert export_resp.status_code == 200, export_resp.text
    rows = _rows(export_resp)
    assert rows[0] == ["expense_date", "category", "currency", "amount", "description"]
    assert any(r[1] == "materials" and r[4] == "Slab delivery" for r in rows[1:])


def test_export_journal_balances_debits_and_credits(app_client, owner_headers, sent_invoice):
    app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "100.00", "method": "cash"},
    )
    app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "materials", "amount": "50.00", "expense_date": "2026-07-01"},
    )

    resp = app_client.get("/api/v1/finance/export/journal", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    rows = _rows(resp)
    assert rows[0] == ["date", "account", "debit", "credit", "reference", "memo"]

    total_debit = sum(float(r[2]) for r in rows[1:] if r[2])
    total_credit = sum(float(r[3]) for r in rows[1:] if r[3])
    assert total_debit == total_credit


def test_export_unknown_resource_404s(app_client, owner_headers):
    resp = app_client.get("/api/v1/finance/export/not-a-real-resource", headers=owner_headers)
    assert resp.status_code == 404


def test_export_requires_permission(app_client, sent_invoice):
    resp = app_client.get("/api/v1/finance/export/invoices")
    assert resp.status_code == 401
