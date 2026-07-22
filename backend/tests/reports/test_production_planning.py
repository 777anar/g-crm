"""Tests for the Production Planning Dashboard (Phase 2 requirement #5):
queues by configurable stage, workload by operator, and overdue
highlighting -- built directly on Phase 1's Production module tables."""
from datetime import date, timedelta


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
        company_id=company.id, material_id=material.id, warehouse_id=warehouse.id,
        slab_number=f"SLB-{suffix}", length_mm="3200", width_mm="1600", area_m2="5.12", status="available",
    )
    db_session.add(slab)
    db_session.flush()

    q = Quote(
        company_id=company.id, project_id=project.id, customer_id=customer.id, version=1,
        quote_number=f"QT-2026-{suffix}-v1", status="accepted", currency="AZN",
    )
    db_session.add(q)
    db_session.flush()
    sec = QuoteSection(company_id=company.id, quote_id=q.id, name="Main Section", sort_order=0)
    db_session.add(sec)
    db_session.flush()
    db_session.add(QuoteSectionItem(
        company_id=company.id, section_id=sec.id, quote_id=q.id, item_type="material", sort_order=0,
        description="Countertop", slab_id=slab.id, quantity="2.5", unit="m2",
        unit_sale_price="150.00", unit_cost_price="100.00", line_total_sale="375.00", line_total_cost="250.00",
    ))
    slab.status = "reserved"
    db_session.commit()

    order = app_client.post("/api/v1/orders", headers=owner_headers, json={"quote_id": str(q.id)}).json()
    resp = app_client.post(
        f"/api/v1/orders/{order['id']}/status", headers=owner_headers, json={"status": "approved_for_production"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_dashboard_lists_active_jobs_with_stage_and_customer_enrichment(
    app_client, owner_headers, db_session, company, project, customer
):
    order = _create_approved_order(app_client, db_session, owner_headers, company, project, customer, "PP1")
    work_order = app_client.post("/api/v1/production", headers=owner_headers, json={"order_id": order["id"]}).json()

    resp = app_client.get("/api/v1/reports/production-planning", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["stages"]) == 8  # the seeded stone-fabrication defaults
    job = next(j for j in body["jobs"] if j["id"] == work_order["id"])
    assert job["customer_name"] == customer.name
    assert job["order_number"] == order["order_number"]
    assert job["status"] == "queued"
    assert job["is_overdue"] is False


def test_dashboard_excludes_completed_and_cancelled_jobs(
    app_client, owner_headers, db_session, company, project, customer
):
    order = _create_approved_order(app_client, db_session, owner_headers, company, project, customer, "PP2")
    work_order = app_client.post("/api/v1/production", headers=owner_headers, json={"order_id": order["id"]}).json()

    for status in ("cutting", "polishing", "quality_check", "completed"):
        app_client.post(f"/api/v1/production/{work_order['id']}/status", headers=owner_headers, json={"status": status})

    resp = app_client.get("/api/v1/reports/production-planning", headers=owner_headers)
    assert not any(j["id"] == work_order["id"] for j in resp.json()["jobs"])


def test_dashboard_highlights_overdue_jobs(app_client, owner_headers, db_session, company, project, customer):
    order = _create_approved_order(app_client, db_session, owner_headers, company, project, customer, "PP3")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": order["id"], "due_date": yesterday}
    ).json()

    resp = app_client.get("/api/v1/reports/production-planning", headers=owner_headers)
    body = resp.json()
    job = next(j for j in body["jobs"] if j["id"] == work_order["id"])
    assert job["is_overdue"] is True
    assert body["overdue_count"] >= 1


def test_dashboard_computes_operator_workload(
    app_client, owner_headers, db_session, company, project, customer, owner_user
):
    order = _create_approved_order(app_client, db_session, owner_headers, company, project, customer, "PP4")
    work_order = app_client.post("/api/v1/production", headers=owner_headers, json={"order_id": order["id"]}).json()
    app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=owner_headers,
        json={"operator_user_id": str(owner_user.id)},
    )

    resp = app_client.get("/api/v1/reports/production-planning", headers=owner_headers)
    body = resp.json()
    workload = next(w for w in body["operator_workload"] if w["operator_id"] == str(owner_user.id))
    assert workload["job_count"] == 1
    assert workload["operator_name"] == owner_user.full_name


def test_dashboard_groups_by_configured_stage(app_client, owner_headers, db_session, company, project, customer):
    order = _create_approved_order(app_client, db_session, owner_headers, company, project, customer, "PP5")
    work_order = app_client.post("/api/v1/production", headers=owner_headers, json={"order_id": order["id"]}).json()

    stages = app_client.get("/api/v1/production/stages", headers=owner_headers).json()["items"]
    cnc_stage = next(s for s in stages if s["name"] == "CNC")
    app_client.post(f"/api/v1/production/{work_order['id']}/stage", headers=owner_headers, json={"stage_id": cnc_stage["id"]})

    resp = app_client.get("/api/v1/reports/production-planning", headers=owner_headers)
    body = resp.json()
    job = next(j for j in body["jobs"] if j["id"] == work_order["id"])
    assert job["stage_id"] == cnc_stage["id"]
    assert job["stage_name"] == "CNC"
