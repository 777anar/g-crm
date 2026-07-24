"""Tests for the automated low-stock -> purchase suggestion endpoint
(Phase 20: Advanced Cut Optimization & Supply Chain Intelligence)."""


def test_low_stock_suggests_material_with_no_available_slabs(app_client, owner_headers, out_of_stock_material, sold_slab):
    resp = app_client.get("/api/v1/reports/inventory/low-stock", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    rows = {m["material_id"]: m for m in body["materials"]}
    assert str(out_of_stock_material.id) in rows
    assert rows[str(out_of_stock_material.id)]["available_slab_count"] == 0
    assert rows[str(out_of_stock_material.id)]["suggested"] is True


def test_low_stock_excludes_well_stocked_material(app_client, owner_headers, material, available_slab):
    resp = app_client.get(
        "/api/v1/reports/inventory/low-stock", headers=owner_headers, params={"stock_threshold": 0}
    )
    assert resp.status_code == 200, resp.text
    rows = {m["material_id"]: m for m in resp.json()["materials"]}
    assert str(material.id) not in rows


def test_low_stock_threshold_is_configurable(app_client, owner_headers, material, available_slab):
    resp = app_client.get(
        "/api/v1/reports/inventory/low-stock", headers=owner_headers, params={"stock_threshold": 5}
    )
    assert resp.status_code == 200, resp.text
    rows = {m["material_id"]: m for m in resp.json()["materials"]}
    assert str(material.id) in rows
    assert rows[str(material.id)]["available_slab_count"] == 1


def test_low_stock_empty_company_returns_no_suggestions(app_client, owner_headers, company):
    resp = app_client.get("/api/v1/reports/inventory/low-stock", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["materials"] == []
