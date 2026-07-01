"""Tests for the Orders module."""
import uuid


def test_create_order_from_accepted_quote(app_client, owner_headers, accepted_quote):
    resp = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "waiting"
    assert body["order_number"].startswith("ORD-")
    assert body["quote_id"] == str(accepted_quote.id)
    assert body["currency"] == "AZN"


def test_create_order_copies_sections_and_items(app_client, owner_headers, accepted_quote):
    resp = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    )
    assert resp.status_code == 200, resp.text
    order_id = resp.json()["id"]

    # Check sections
    sections_resp = app_client.get(
        f"/api/v1/orders/{order_id}/sections",
        headers=owner_headers,
    )
    assert sections_resp.status_code == 200
    sections = sections_resp.json()["items"]
    assert len(sections) == 1
    assert sections[0]["name"] == "Main Section"

    section_id = sections[0]["id"]

    # Check items
    items_resp = app_client.get(
        f"/api/v1/orders/{order_id}/sections/{section_id}/items",
        headers=owner_headers,
    )
    assert items_resp.status_code == 200
    items = items_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["description"] == "Marble countertop"
    assert items[0]["item_type"] == "material"

    # Check measurements
    meas_resp = app_client.get(
        f"/api/v1/orders/{order_id}/sections/{section_id}/measurements",
        headers=owner_headers,
    )
    assert meas_resp.status_code == 200
    measurements = meas_resp.json()["items"]
    assert len(measurements) == 1
    assert measurements[0]["label"] == "Island top"


def test_create_order_from_non_accepted_quote_returns_422(app_client, owner_headers, draft_quote):
    resp = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(draft_quote.id)},
    )
    assert resp.status_code == 422, resp.text


def test_list_orders(app_client, owner_headers, accepted_quote):
    app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    )
    resp = app_client.get("/api/v1/orders", headers=owner_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


def test_get_order(app_client, owner_headers, accepted_quote):
    order_id = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    ).json()["id"]

    resp = app_client.get(f"/api/v1/orders/{order_id}", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


def test_update_order_mutable_fields(app_client, owner_headers, accepted_quote):
    order_id = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    ).json()["id"]

    resp = app_client.patch(
        f"/api/v1/orders/{order_id}",
        headers=owner_headers,
        json={
            "notes": "Handle with care",
            "delivery_address": "123 Main St",
            "scheduled_production_date": "2026-08-01",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["notes"] == "Handle with care"
    assert body["delivery_address"] == "123 Main St"
    assert body["scheduled_production_date"] == "2026-08-01"


def test_valid_status_transitions(app_client, owner_headers, accepted_quote):
    order_id = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    ).json()["id"]

    # waiting → approved_for_production → in_production → ready → delivered → installed → completed
    transitions = [
        "approved_for_production",
        "in_production",
        "ready",
        "delivered",
        "installed",
        "completed",
    ]
    for new_status in transitions:
        resp = app_client.post(
            f"/api/v1/orders/{order_id}/status",
            headers=owner_headers,
            json={"status": new_status},
        )
        assert resp.status_code == 200, f"Failed on transition to {new_status}: {resp.text}"
        assert resp.json()["status"] == new_status


def test_invalid_status_transition_returns_422(app_client, owner_headers, accepted_quote):
    order_id = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    ).json()["id"]

    # waiting → completed is invalid
    resp = app_client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=owner_headers,
        json={"status": "completed"},
    )
    assert resp.status_code == 422, resp.text


def test_cancel_order(app_client, owner_headers, accepted_quote):
    order_id = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    ).json()["id"]

    resp = app_client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=owner_headers,
        json={"status": "cancelled", "cancelled_reason": "Customer changed mind"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_update_item_production_status(app_client, owner_headers, accepted_quote):
    order_id = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    ).json()["id"]

    sections_resp = app_client.get(f"/api/v1/orders/{order_id}/sections", headers=owner_headers)
    section_id = sections_resp.json()["items"][0]["id"]

    items_resp = app_client.get(
        f"/api/v1/orders/{order_id}/sections/{section_id}/items",
        headers=owner_headers,
    )
    item_id = items_resp.json()["items"][0]["id"]

    resp = app_client.patch(
        f"/api/v1/orders/{order_id}/items/{item_id}",
        headers=owner_headers,
        json={"production_status": "cutting", "installation_status": "pending"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["production_status"] == "cutting"
    assert body["installation_status"] == "pending"
