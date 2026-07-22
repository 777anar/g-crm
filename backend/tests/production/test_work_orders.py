"""Tests for the Production module."""


def _create_approved_order(app_client, db_session, owner_headers, company, project, customer, suffix):
    from modules.catalog.infrastructure.models.brand import Brand
    from modules.catalog.infrastructure.models.material import StoneMaterial
    from modules.catalog.infrastructure.models.slab import Slab
    from modules.catalog.infrastructure.models.warehouse import Warehouse
    from modules.sales.infrastructure.models.quote import Quote
    from modules.sales.infrastructure.models.quote_section import QuoteSection
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    brand = Brand(company_id=company.id, name=f"NEOLITH {suffix}")
    db_session.add(brand)
    db_session.flush()
    material = StoneMaterial(company_id=company.id, brand_id=brand.id, name="Calacatta Gold")
    db_session.add(material)
    db_session.flush()
    warehouse = Warehouse(company_id=company.id, name="Main Warehouse")
    db_session.add(warehouse)
    db_session.flush()
    slab = Slab(
        company_id=company.id,
        material_id=material.id,
        warehouse_id=warehouse.id,
        slab_number=f"SLB-{suffix}",
        length_mm="3200",
        width_mm="1600",
        area_m2="5.12",
        status="available",
    )
    db_session.add(slab)
    db_session.flush()

    q = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer.id,
        version=1,
        quote_number=f"QT-2026-{suffix}-v1",
        status="accepted",
        currency="AZN",
    )
    db_session.add(q)
    db_session.flush()
    sec = QuoteSection(company_id=company.id, quote_id=q.id, name="Main Section", sort_order=0)
    db_session.add(sec)
    db_session.flush()
    db_session.add(
        QuoteSectionItem(
            company_id=company.id,
            section_id=sec.id,
            quote_id=q.id,
            item_type="material",
            sort_order=0,
            description="Marble countertop",
            slab_id=slab.id,
            quantity="2.5",
            unit="m2",
            unit_sale_price="150.00",
            unit_cost_price="100.00",
            line_total_sale="375.00",
            line_total_cost="250.00",
        )
    )
    slab.status = "reserved"
    db_session.commit()

    order = app_client.post("/api/v1/orders", headers=owner_headers, json={"quote_id": str(q.id)}).json()
    resp = app_client.post(
        f"/api/v1/orders/{order['id']}/status", headers=owner_headers, json={"status": "approved_for_production"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_work_orders_cursor_reaches_the_next_page(app_client, owner_headers, db_session, company, project, customer):
    work_order_ids = []
    for i in range(3):
        order = _create_approved_order(app_client, db_session, owner_headers, company, project, customer, f"CUR{i}")
        resp = app_client.post("/api/v1/production", headers=owner_headers, json={"order_id": order["id"]})
        assert resp.status_code == 200, resp.text
        work_order_ids.append(resp.json()["id"])

    first_page = app_client.get("/api/v1/production", headers=owner_headers, params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = app_client.get(
        "/api/v1/production", headers=owner_headers, params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None

    first_ids = {w["id"] for w in first_page["items"]}
    second_ids = {w["id"] for w in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == set(work_order_ids)


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


def test_full_work_order_lifecycle_completes_order_and_consumes_slab(
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
    assert slab.status == "consumed"

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
