def test_create_and_list_brand(app_client, owner_headers):
    response = app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "NEOLITH"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "NEOLITH"
    assert body["status"] == "active"

    listed = app_client.get("/api/v1/catalog/brands", headers=owner_headers).json()
    assert any(b["name"] == "NEOLITH" for b in listed["items"])


def test_create_brand_requires_write_permission(app_client, viewer_headers):
    response = app_client.post("/api/v1/catalog/brands", headers=viewer_headers, json={"name": "INALCO"})
    assert response.status_code == 403


def test_update_brand_to_hidden_excludes_it_from_default_list(app_client, owner_headers):
    created = app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "BELENCO"}).json()
    app_client.patch(f"/api/v1/catalog/brands/{created['id']}", headers=owner_headers, json={"status": "hidden"})

    active_only = app_client.get("/api/v1/catalog/brands", headers=owner_headers).json()
    assert created["id"] not in [b["id"] for b in active_only["items"]]

    with_hidden = app_client.get(
        "/api/v1/catalog/brands", headers=owner_headers, params={"include_hidden": True}
    ).json()
    assert created["id"] in [b["id"] for b in with_hidden["items"]]


def test_brand_search(app_client, owner_headers):
    for name in ["CAESARSTONE", "SAPIENSTONE", "ANATOLIA"]:
        app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": name})

    response = app_client.get("/api/v1/catalog/brands", headers=owner_headers, params={"search": "stone"})
    names = {b["name"] for b in response.json()["items"]}
    assert names == {"CAESARSTONE", "SAPIENSTONE"}


def test_brands_cursor_reaches_the_next_page(app_client, owner_headers):
    names = [f"Cursor Brand {i}" for i in range(3)]
    for name in names:
        app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": name})

    first_page = app_client.get("/api/v1/catalog/brands", headers=owner_headers, params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = app_client.get(
        "/api/v1/catalog/brands", headers=owner_headers, params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None

    first_ids = {b["id"] for b in first_page["items"]}
    second_ids = {b["id"] for b in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_get_brand_not_found(app_client, owner_headers):
    import uuid

    response = app_client.get(f"/api/v1/catalog/brands/{uuid.uuid4()}", headers=owner_headers)
    assert response.status_code == 404


def test_create_collection_requires_existing_brand(app_client, owner_headers):
    import uuid

    response = app_client.post(
        "/api/v1/catalog/collections", headers=owner_headers, json={"brand_id": str(uuid.uuid4()), "name": "Calacatta"}
    )
    assert response.status_code == 404


def test_create_and_list_collection(app_client, owner_headers):
    brand = app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "NEOLITH"}).json()
    response = app_client.post(
        "/api/v1/catalog/collections", headers=owner_headers, json={"brand_id": brand["id"], "name": "Calacatta"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["brand_id"] == brand["id"]

    listed = app_client.get(
        "/api/v1/catalog/collections", headers=owner_headers, params={"brand_id": brand["id"]}
    ).json()
    assert len(listed["items"]) == 1
    assert listed["items"][0]["name"] == "Calacatta"


def test_update_collection(app_client, owner_headers):
    brand = app_client.post("/api/v1/catalog/brands", headers=owner_headers, json={"name": "INALCO"}).json()
    collection = app_client.post(
        "/api/v1/catalog/collections", headers=owner_headers, json={"brand_id": brand["id"], "name": "Compac"}
    ).json()

    response = app_client.patch(
        f"/api/v1/catalog/collections/{collection['id']}", headers=owner_headers, json={"name": "Compac Pro"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Compac Pro"
