"""Tests for sections, measurements, and items within a quote."""


def _create_project_and_quote(client, headers, customer_id):
    proj = client.post(
        "/api/v1/sales/projects",
        headers=headers,
        json={"customer_id": str(customer_id), "name": "Renovation"},
    ).json()
    quote = client.post(
        f"/api/v1/sales/projects/{proj['id']}/quotes",
        headers=headers,
        json={},
    ).json()
    return proj, quote


def test_create_and_list_sections(app_client, owner_headers, customer):
    _, quote = _create_project_and_quote(app_client, owner_headers, customer.id)
    resp = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/sections",
        headers=owner_headers,
        json={"name": "Kitchen", "sort_order": 1},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Kitchen"

    list_resp = app_client.get(
        f"/api/v1/sales/quotes/{quote['id']}/sections", headers=owner_headers
    )
    assert len(list_resp.json()["items"]) == 1


def test_update_section(app_client, owner_headers, customer):
    _, quote = _create_project_and_quote(app_client, owner_headers, customer.id)
    section = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/sections",
        headers=owner_headers,
        json={"name": "Bathroom"},
    ).json()
    resp = app_client.patch(
        f"/api/v1/sales/sections/{section['id']}",
        headers=owner_headers,
        json={"name": "Main Bathroom"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Main Bathroom"


def test_delete_section(app_client, owner_headers, customer):
    _, quote = _create_project_and_quote(app_client, owner_headers, customer.id)
    section = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/sections",
        headers=owner_headers,
        json={"name": "Island"},
    ).json()
    resp = app_client.delete(
        f"/api/v1/sales/sections/{section['id']}", headers=owner_headers
    )
    assert resp.status_code == 204
    list_resp = app_client.get(
        f"/api/v1/sales/quotes/{quote['id']}/sections", headers=owner_headers
    )
    assert len(list_resp.json()["items"]) == 0


def test_create_measurement_and_area_computed(app_client, owner_headers, customer):
    _, quote = _create_project_and_quote(app_client, owner_headers, customer.id)
    section = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/sections",
        headers=owner_headers,
        json={"name": "Kitchen"},
    ).json()
    resp = app_client.post(
        f"/api/v1/sales/sections/{section['id']}/measurements",
        headers=owner_headers,
        json={
            "label": "Countertop",
            "length_mm": "3000",
            "width_mm": "600",
            "quantity": 1,
            "waste_pct": "10",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # area_m2 = 3000 * 600 * 1 / 1_000_000 = 1.8
    assert float(body["area_m2"]) == 1.8
    # required_area_m2 = 1.8 * 1.1 = 1.98
    assert float(body["required_area_m2"]) == 1.98


def test_create_item_and_totals_cascaded(app_client, owner_headers, customer):
    _, quote = _create_project_and_quote(app_client, owner_headers, customer.id)
    section = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/sections",
        headers=owner_headers,
        json={"name": "Kitchen"},
    ).json()
    resp = app_client.post(
        f"/api/v1/sales/sections/{section['id']}/items",
        headers=owner_headers,
        json={
            "item_type": "material",
            "description": "Calacatta Gold",
            "quantity": "2.5",
            "unit": "m2",
            "unit_sale_price": "120.00",
            "unit_cost_price": "80.00",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert float(body["line_total_sale"]) == 300.0
    assert float(body["line_total_cost"]) == 200.0

    # Quote totals should be recomputed
    q = app_client.get(f"/api/v1/sales/quotes/{quote['id']}", headers=owner_headers).json()
    assert float(q["subtotal_gross"]) == 300.0


def test_item_invalid_type_rejected(app_client, owner_headers, customer):
    _, quote = _create_project_and_quote(app_client, owner_headers, customer.id)
    section = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/sections",
        headers=owner_headers,
        json={"name": "Test"},
    ).json()
    resp = app_client.post(
        f"/api/v1/sales/sections/{section['id']}/items",
        headers=owner_headers,
        json={"item_type": "flying_carpet", "quantity": "1"},
    )
    assert resp.status_code in (400, 422)


def test_delete_item_recalculates_totals(app_client, owner_headers, customer):
    _, quote = _create_project_and_quote(app_client, owner_headers, customer.id)
    section = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/sections",
        headers=owner_headers,
        json={"name": "Kitchen"},
    ).json()
    item = app_client.post(
        f"/api/v1/sales/sections/{section['id']}/items",
        headers=owner_headers,
        json={
            "item_type": "material",
            "quantity": "1",
            "unit_sale_price": "100.00",
        },
    ).json()
    app_client.delete(f"/api/v1/sales/items/{item['id']}", headers=owner_headers)
    q = app_client.get(f"/api/v1/sales/quotes/{quote['id']}", headers=owner_headers).json()
    assert float(q["subtotal_gross"]) == 0.0


def test_service_prices_upsert_and_list(app_client, owner_headers):
    resp = app_client.put(
        "/api/v1/sales/service-prices",
        headers=owner_headers,
        json={"service_key": "sink_cutout", "sale_price": "150.00", "cost_price": "80.00"},
    )
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["sale_price"]) == 150.0

    list_resp = app_client.get("/api/v1/sales/service-prices", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 1
