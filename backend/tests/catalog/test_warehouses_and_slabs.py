import uuid


def _brand_and_material(client, headers, brand_name="NEOLITH", material_name="Calacatta Gold"):
    brand = client.post("/api/v1/catalog/brands", headers=headers, json={"name": brand_name}).json()
    material = client.post(
        "/api/v1/catalog/materials", headers=headers, json={"brand_id": brand["id"], "name": material_name}
    ).json()
    return brand, material


def _warehouse(client, headers, name="Baku Main Warehouse"):
    return client.post("/api/v1/catalog/warehouses", headers=headers, json={"name": name}).json()


def test_create_and_list_warehouse(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/catalog/warehouses", headers=owner_headers, json={"name": "Baku Main Warehouse", "address": "Baku, AZ"}
    )
    assert response.status_code == 200
    listed = app_client.get("/api/v1/catalog/warehouses", headers=owner_headers).json()
    assert any(w["name"] == "Baku Main Warehouse" for w in listed["items"])


def test_create_slab_requires_existing_material_and_warehouse(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": str(uuid.uuid4()), "warehouse_id": str(uuid.uuid4()), "slab_number": "SL-0001"},
    )
    assert response.status_code == 404


def test_create_slab_computes_area_from_dimensions(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)

    response = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={
            "material_id": material["id"],
            "warehouse_id": warehouse["id"],
            "slab_number": "SL-0001",
            "length_mm": "3200",
            "width_mm": "1600",
            "weight_kg": "120.5",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "available"
    assert float(body["area_m2"]) == 5.12


def test_create_slab_rejects_duplicate_slab_number(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    payload = {"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-DUPLICATE"}

    first = app_client.post("/api/v1/catalog/slabs", headers=owner_headers, json=payload)
    assert first.status_code == 200

    second = app_client.post("/api/v1/catalog/slabs", headers=owner_headers, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_slab_status_transition_available_to_reserved_to_sold(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-0002"},
    ).json()

    reserved = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "reserved"}
    )
    assert reserved.status_code == 200
    assert reserved.json()["status"] == "reserved"

    sold = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "sold"}
    )
    assert sold.status_code == 200
    assert sold.json()["status"] == "sold"


def test_slab_status_transition_rejects_sold_to_available(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-0003", "status": "sold"},
    ).json()

    response = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "available"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_slab_status_scrap_reachable_from_available(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-0004"},
    ).json()

    response = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "scrap"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "scrap"


def test_list_slabs_filter_by_material_and_warehouse(app_client, owner_headers):
    _, material_a = _brand_and_material(app_client, owner_headers, "NEOLITH", "Material A")
    _, material_b = _brand_and_material(app_client, owner_headers, "NEOLITH", "Material B")
    warehouse = _warehouse(app_client, owner_headers)

    app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": material_a["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-A1"},
    )
    app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": material_b["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-B1"},
    )

    response = app_client.get(
        "/api/v1/catalog/slabs", headers=owner_headers, params={"material_id": material_a["id"]}
    )
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["slab_number"] == "SL-A1"


def test_search_slabs_by_slab_number(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": "SL-FINDME"},
    )

    response = app_client.get("/api/v1/catalog/slabs", headers=owner_headers, params={"search": "FINDME"})
    assert len(response.json()["items"]) == 1
