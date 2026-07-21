"""Tests for the Purchasing module's Supplier CRUD."""


def test_create_and_get_supplier(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/purchasing/suppliers",
        headers=owner_headers,
        json={"name": "Antolini", "contact_name": "Marco Rossi", "phone": "+39 011 1234567"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Antolini"
    assert body["status"] == "active"

    get_resp = app_client.get(f"/api/v1/purchasing/suppliers/{body['id']}", headers=owner_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["contact_name"] == "Marco Rossi"


def test_create_supplier_requires_write_permission(app_client, viewer_headers):
    resp = app_client.post("/api/v1/purchasing/suppliers", headers=viewer_headers, json={"name": "Antolini"})
    assert resp.status_code == 403


def test_update_supplier_to_hidden_excludes_it_from_default_list(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/purchasing/suppliers", headers=owner_headers, json={"name": "Levantina"}
    ).json()
    app_client.patch(
        f"/api/v1/purchasing/suppliers/{created['id']}", headers=owner_headers, json={"status": "hidden"}
    )

    active_only = app_client.get("/api/v1/purchasing/suppliers", headers=owner_headers).json()
    assert created["id"] not in [s["id"] for s in active_only["items"]]

    with_hidden = app_client.get(
        "/api/v1/purchasing/suppliers", headers=owner_headers, params={"include_hidden": True}
    ).json()
    assert created["id"] in [s["id"] for s in with_hidden["items"]]


def test_supplier_search(app_client, owner_headers):
    for name in ["Caesarstone Supply", "Silestone Direct", "Antolini Import"]:
        app_client.post("/api/v1/purchasing/suppliers", headers=owner_headers, json={"name": name})

    resp = app_client.get("/api/v1/purchasing/suppliers", headers=owner_headers, params={"search": "stone"})
    names = {s["name"] for s in resp.json()["items"]}
    assert names == {"Caesarstone Supply", "Silestone Direct"}


def test_invalid_supplier_status_rejected(app_client, owner_headers, supplier):
    resp = app_client.patch(
        f"/api/v1/purchasing/suppliers/{supplier['id']}", headers=owner_headers, json={"status": "on_vacation"}
    )
    assert resp.status_code == 400, resp.text


def test_get_supplier_not_found(app_client, owner_headers):
    import uuid

    resp = app_client.get(f"/api/v1/purchasing/suppliers/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


def test_suppliers_cursor_reaches_the_next_page(app_client, owner_headers):
    ids = []
    for name in ["Supplier A", "Supplier B", "Supplier C"]:
        resp = app_client.post("/api/v1/purchasing/suppliers", headers=owner_headers, json={"name": name})
        ids.append(resp.json()["id"])

    first_page = app_client.get("/api/v1/purchasing/suppliers", headers=owner_headers, params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = app_client.get(
        "/api/v1/purchasing/suppliers", headers=owner_headers, params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None

    first_ids = {s["id"] for s in first_page["items"]}
    second_ids = {s["id"] for s in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == set(ids)
