def _material(client, headers):
    brand = client.post("/api/v1/catalog/brands", headers=headers, json={"name": "NEOLITH"}).json()
    return client.post(
        "/api/v1/catalog/materials", headers=headers, json={"brand_id": brand["id"], "name": "Calacatta Gold"}
    ).json()


def test_create_price_list(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/catalog/price-lists", headers=owner_headers, json={"name": "Retail 2026", "currency": "AZN"}
    )
    assert response.status_code == 200
    assert response.json()["currency"] == "AZN"


def test_upsert_price_list_entry_creates_then_updates(app_client, owner_headers):
    material = _material(app_client, owner_headers)
    price_list = app_client.post(
        "/api/v1/catalog/price-lists", headers=owner_headers, json={"name": "Retail 2026"}
    ).json()

    created = app_client.put(
        f"/api/v1/catalog/price-lists/{price_list['id']}/entries",
        headers=owner_headers,
        json={"material_id": material["id"], "cost_price": "100.00", "sale_price": "180.00"},
    )
    assert created.status_code == 200
    assert created.json()["sale_price"] == "180.00"

    updated = app_client.put(
        f"/api/v1/catalog/price-lists/{price_list['id']}/entries",
        headers=owner_headers,
        json={"material_id": material["id"], "cost_price": "100.00", "sale_price": "190.00"},
    )
    assert updated.status_code == 200
    assert updated.json()["sale_price"] == "190.00"
    # Same material in the same price list -- upsert, not a second row.
    assert updated.json()["id"] == created.json()["id"]

    entries = app_client.get(
        f"/api/v1/catalog/price-lists/{price_list['id']}/entries", headers=owner_headers
    ).json()
    assert len(entries["items"]) == 1


def test_price_list_entry_requires_existing_material(app_client, owner_headers):
    import uuid

    price_list = app_client.post(
        "/api/v1/catalog/price-lists", headers=owner_headers, json={"name": "Retail 2026"}
    ).json()
    response = app_client.put(
        f"/api/v1/catalog/price-lists/{price_list['id']}/entries",
        headers=owner_headers,
        json={"material_id": str(uuid.uuid4()), "cost_price": "1", "sale_price": "2"},
    )
    assert response.status_code == 404


def test_list_prices_for_material_across_price_lists(app_client, owner_headers):
    material = _material(app_client, owner_headers)
    retail = app_client.post("/api/v1/catalog/price-lists", headers=owner_headers, json={"name": "Retail"}).json()
    wholesale = app_client.post(
        "/api/v1/catalog/price-lists", headers=owner_headers, json={"name": "Wholesale"}
    ).json()

    app_client.put(
        f"/api/v1/catalog/price-lists/{retail['id']}/entries",
        headers=owner_headers,
        json={"material_id": material["id"], "cost_price": "100", "sale_price": "180"},
    )
    app_client.put(
        f"/api/v1/catalog/price-lists/{wholesale['id']}/entries",
        headers=owner_headers,
        json={"material_id": material["id"], "cost_price": "100", "sale_price": "130"},
    )

    response = app_client.get(f"/api/v1/catalog/materials/{material['id']}/prices", headers=owner_headers)
    items = response.json()["items"]
    assert len(items) == 2
    sale_prices = {item["sale_price"] for item in items}
    assert sale_prices == {"180.00", "130.00"}
