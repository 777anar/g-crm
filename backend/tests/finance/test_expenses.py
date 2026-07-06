"""Tests for the Finance module's expense tracking."""


def test_create_general_expense(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "rent", "amount": "500.00", "expense_date": "2026-07-01", "description": "July rent"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["category"] == "rent"
    assert body["amount"] == "500.00"
    assert body["order_id"] is None


def test_create_expense_linked_to_order(app_client, owner_headers, ready_order):
    resp = app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={
            "category": "transport",
            "amount": "75.00",
            "expense_date": "2026-07-02",
            "order_id": ready_order["id"],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["order_id"] == ready_order["id"]


def test_create_expense_with_unknown_order_returns_404(app_client, owner_headers):
    import uuid

    resp = app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "transport", "amount": "75.00", "expense_date": "2026-07-02", "order_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404, resp.text


def test_negative_expense_amount_rejected(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "other", "amount": "-10.00", "expense_date": "2026-07-01"},
    )
    assert resp.status_code == 422, resp.text


def test_invalid_expense_category_rejected(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "bribes", "amount": "10.00", "expense_date": "2026-07-01"},
    )
    assert resp.status_code == 400, resp.text


def test_list_expenses_filters_by_category(app_client, owner_headers):
    app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "rent", "amount": "500.00", "expense_date": "2026-07-01"},
    )
    app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "utilities", "amount": "120.00", "expense_date": "2026-07-01"},
    )

    resp = app_client.get("/api/v1/finance/expenses", headers=owner_headers, params={"category": "rent"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["category"] == "rent"


def test_get_expense(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "labor", "amount": "300.00", "expense_date": "2026-07-01"},
    ).json()

    resp = app_client.get(f"/api/v1/finance/expenses/{created['id']}", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
