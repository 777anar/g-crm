"""Tests for the Production module."""


def test_create_work_order_reserves_slab_and_advances_order(app_client, owner_headers, approved_order, slab, db_session):
    resp = app_client.post(
        "/api/v1/production",
        headers=owner_headers,
        json={"order_id": approved_order["id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "queued"
    assert body["work_order_number"].startswith("WO-")
    assert body["order_id"] == approved_order["id"]

    db_session.refresh(slab)
    assert slab.status == "in_production"

    order_resp = app_client.get(f"/api/v1/orders/{approved_order['id']}", headers=owner_headers)
    assert order_resp.json()["status"] == "in_production"


def test_create_work_order_requires_approved_for_production(app_client, owner_headers, accepted_quote_with_slab):
    order = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote_with_slab.id)},
    ).json()

    resp = app_client.post(
        "/api/v1/production",
        headers=owner_headers,
        json={"order_id": order["id"]},
    )
    assert resp.status_code == 422, resp.text


def test_create_work_order_twice_returns_422(app_client, owner_headers, approved_order):
    first = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    )
    assert first.status_code == 200, first.text

    second = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    )
    assert second.status_code == 422, second.text


def test_work_order_items_lists_slab_details(app_client, owner_headers, approved_order, slab):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.get(f"/api/v1/production/{work_order['id']}/items", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["slab_number"] == slab.slab_number
    assert items[0]["description"] == "Marble countertop"


def test_full_work_order_lifecycle_completes_order_and_sells_slab(
    app_client, owner_headers, approved_order, slab, db_session
):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    for status in ("cutting", "polishing", "quality_check", "completed"):
        resp = app_client.post(
            f"/api/v1/production/{work_order['id']}/status",
            headers=owner_headers,
            json={"status": status},
        )
        assert resp.status_code == 200, f"Failed on transition to {status}: {resp.text}"
        assert resp.json()["status"] == status

    db_session.refresh(slab)
    assert slab.status == "sold"

    order_resp = app_client.get(f"/api/v1/orders/{approved_order['id']}", headers=owner_headers)
    assert order_resp.json()["status"] == "ready"

    sections = app_client.get(f"/api/v1/orders/{approved_order['id']}/sections", headers=owner_headers).json()["items"]
    items = app_client.get(
        f"/api/v1/orders/{approved_order['id']}/sections/{sections[0]['id']}/items", headers=owner_headers
    ).json()["items"]
    assert items[0]["production_status"] == "done"


def test_invalid_work_order_transition_returns_422(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/status",
        headers=owner_headers,
        json={"status": "completed"},
    )
    assert resp.status_code == 422, resp.text


def test_cancel_work_order_releases_slab(app_client, owner_headers, approved_order, slab, db_session):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/status",
        headers=owner_headers,
        json={"status": "cancelled", "cancelled_reason": "Slab cracked"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"

    db_session.refresh(slab)
    assert slab.status == "available"


def test_list_and_get_work_order(app_client, owner_headers, approved_order):
    created = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    list_resp = app_client.get("/api/v1/production", headers=owner_headers)
    assert list_resp.status_code == 200
    assert any(wo["id"] == created["id"] for wo in list_resp.json()["items"])

    by_order_resp = app_client.get(f"/api/v1/production/by-order/{approved_order['id']}", headers=owner_headers)
    assert by_order_resp.status_code == 200
    assert by_order_resp.json()["id"] == created["id"]
