import uuid


def _create_brand(client, headers, name="NEOLITH"):
    return client.post("/api/v1/catalog/brands", headers=headers, json={"name": name}).json()


def test_create_material_requires_existing_brand(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/catalog/materials",
        headers=owner_headers,
        json={"brand_id": str(uuid.uuid4()), "name": "Calacatta Gold"},
    )
    assert response.status_code == 404


def test_create_material_full_fields(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    response = app_client.post(
        "/api/v1/catalog/materials",
        headers=owner_headers,
        json={
            "brand_id": brand["id"],
            "name": "Calacatta Gold",
            "material_type": "Sintered Stone",
            "color": "White/Gold",
            "finish": "Polished",
            "thickness_mm": "12",
            "dimensions": "3200x1600mm",
            "country_of_origin": "Spain",
            "description": "Premium sintered stone slab.",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Calacatta Gold"
    assert body["status"] == "active"
    assert body["dimensions"] == "3200x1600mm"


def test_create_material_rejects_collection_from_different_brand(app_client, owner_headers):
    brand_a = _create_brand(app_client, owner_headers, "NEOLITH")
    brand_b = _create_brand(app_client, owner_headers, "INALCO")
    collection_b = app_client.post(
        "/api/v1/catalog/collections", headers=owner_headers, json={"brand_id": brand_b["id"], "name": "Compac"}
    ).json()

    response = app_client.post(
        "/api/v1/catalog/materials",
        headers=owner_headers,
        json={"brand_id": brand_a["id"], "collection_id": collection_b["id"], "name": "Mismatched"},
    )
    assert response.status_code in (400, 422)


def test_create_material_rejects_invalid_status(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    response = app_client.post(
        "/api/v1/catalog/materials",
        headers=owner_headers,
        json={"brand_id": brand["id"], "name": "X", "status": "deleted"},
    )
    assert response.status_code in (400, 422)


def test_list_materials_filter_by_brand(app_client, owner_headers):
    brand_a = _create_brand(app_client, owner_headers, "NEOLITH")
    brand_b = _create_brand(app_client, owner_headers, "CAESARSTONE")
    app_client.post("/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand_a["id"], "name": "A1"})
    app_client.post("/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand_b["id"], "name": "B1"})

    filtered = app_client.get(
        "/api/v1/catalog/materials", headers=owner_headers, params={"brand_id": brand_a["id"]}
    ).json()
    assert len(filtered["items"]) == 1
    assert filtered["items"][0]["name"] == "A1"


def test_search_materials(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    app_client.post(
        "/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand["id"], "name": "Calacatta Gold"}
    )
    app_client.post(
        "/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand["id"], "name": "Statuario"}
    )

    response = app_client.get("/api/v1/catalog/materials", headers=owner_headers, params={"search": "Calacatta"})
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Calacatta Gold"


def test_sort_materials_by_name(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    for name in ["Zebrino", "Arabescato"]:
        app_client.post("/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand["id"], "name": name})

    response = app_client.get("/api/v1/catalog/materials", headers=owner_headers, params={"sort": "name"})
    names = [m["name"] for m in response.json()["items"]]
    assert names == sorted(names)


def test_materials_pagination_next_cursor(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    for i in range(3):
        app_client.post(
            "/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand["id"], "name": f"Material {i}"}
        )

    first_page = app_client.get("/api/v1/catalog/materials", headers=owner_headers, params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = app_client.get(
        "/api/v1/catalog/materials", headers=owner_headers, params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None


def test_update_material(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    material = app_client.post(
        "/api/v1/catalog/materials", headers=owner_headers, json={"brand_id": brand["id"], "name": "Original"}
    ).json()

    response = app_client.patch(
        f"/api/v1/catalog/materials/{material['id']}", headers=owner_headers, json={"color": "Beige", "status": "hidden"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["color"] == "Beige"
    assert body["status"] == "hidden"
