"""Tests for the Orders module."""
import uuid


def _create_accepted_quote(db_session, company, project, customer, quote_number):
    from modules.sales.infrastructure.models.quote import Quote
    from modules.sales.infrastructure.models.quote_section import QuoteSection
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    q = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer.id,
        version=1,
        quote_number=quote_number,
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
            quantity="1",
            unit="m2",
            unit_sale_price="100.00",
            unit_cost_price="80.00",
            line_total_sale="100.00",
            line_total_cost="80.00",
        )
    )
    db_session.commit()
    return q


def test_orders_cursor_reaches_the_next_page(app_client, owner_headers, db_session, company, project, customer):
    order_ids = []
    for i in range(3):
        quote = _create_accepted_quote(db_session, company, project, customer, f"QT-2026-CUR{i}-v1")
        resp = app_client.post("/api/v1/orders", headers=owner_headers, json={"quote_id": str(quote.id)})
        assert resp.status_code == 200, resp.text
        order_ids.append(resp.json()["id"])

    first_page = app_client.get("/api/v1/orders", headers=owner_headers, params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = app_client.get(
        "/api/v1/orders", headers=owner_headers, params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None

    first_ids = {o["id"] for o in first_page["items"]}
    second_ids = {o["id"] for o in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == set(order_ids)


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


def test_create_order_adopts_reservation_for_slab_linked_item(
    app_client, owner_headers, db_session, company, project, customer
):
    """Phase 1 (Material Reservation): a quote item with a slab already
    attached is `reserved` at quote-acceptance time (Sales'
    UpdateQuoteStatusUseCase); creating the Order from that quote must
    backfill a formal, queryable SlabReservation row for it -- without
    re-validating availability, since the slab is already known-reserved."""
    from modules.catalog.infrastructure.models.brand import Brand
    from modules.catalog.infrastructure.models.material import StoneMaterial
    from modules.catalog.infrastructure.models.slab import Slab
    from modules.catalog.infrastructure.models.warehouse import Warehouse
    from modules.sales.infrastructure.models.quote import Quote
    from modules.sales.infrastructure.models.quote_section import QuoteSection
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    brand = Brand(company_id=company.id, name="NEOLITH")
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
        slab_number="SL-ADOPT-1",
        status="reserved",
    )
    db_session.add(slab)
    db_session.flush()

    quote = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer.id,
        version=1,
        quote_number="QT-2026-ADOPT-v1",
        status="accepted",
        currency="AZN",
    )
    db_session.add(quote)
    db_session.flush()
    section = QuoteSection(company_id=company.id, quote_id=quote.id, name="Main Section", sort_order=0)
    db_session.add(section)
    db_session.flush()
    db_session.add(QuoteSectionItem(
        company_id=company.id,
        section_id=section.id,
        quote_id=quote.id,
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
    ))
    db_session.commit()

    order = app_client.post("/api/v1/orders", headers=owner_headers, json={"quote_id": str(quote.id)}).json()

    reservations = app_client.get(
        "/api/v1/catalog/reservations", headers=owner_headers, params={"order_id": order["id"]}
    ).json()["items"]
    assert len(reservations) == 1
    assert reservations[0]["slab_id"] == str(slab.id)
    assert reservations[0]["status"] == "active"

    # The slab's own status is untouched (already `reserved` before the
    # order existed) -- adoption only records the bookkeeping row.
    db_session.refresh(slab)
    assert slab.status == "reserved"
