"""Tests for Sprint 4's normalized Material Thickness/Size options -- the
Brand -> Stone -> Thickness -> Size selector's data layer."""
from core.audit.models import AuditLog


def _create_brand(client, headers, name="NEOLITH"):
    return client.post("/api/v1/catalog/brands", headers=headers, json={"name": name}).json()


def _create_material(client, headers, brand_id, name="Calacatta Gold"):
    return client.post(
        "/api/v1/catalog/materials", headers=headers, json={"brand_id": brand_id, "name": name}
    ).json()


def test_add_and_list_thicknesses(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    material = _create_material(app_client, owner_headers, brand["id"])

    resp = app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/thicknesses",
        headers=owner_headers,
        json={"thickness_mm": "12", "sort_order": 1},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["thickness_mm"] == "12"

    app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/thicknesses",
        headers=owner_headers,
        json={"thickness_mm": "20", "sort_order": 2},
    )

    list_resp = app_client.get(f"/api/v1/catalog/materials/{material['id']}/thicknesses", headers=owner_headers)
    items = list_resp.json()["items"]
    assert len(items) == 2
    assert [i["thickness_mm"] for i in items] == ["12", "20"]


def test_thicknesses_are_scoped_to_their_material(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    material_a = _create_material(app_client, owner_headers, brand["id"], "Calacatta Gold")
    material_b = _create_material(app_client, owner_headers, brand["id"], "Marquina Black")

    app_client.post(
        f"/api/v1/catalog/materials/{material_a['id']}/thicknesses",
        headers=owner_headers,
        json={"thickness_mm": "12"},
    )
    app_client.post(
        f"/api/v1/catalog/materials/{material_b['id']}/thicknesses",
        headers=owner_headers,
        json={"thickness_mm": "30"},
    )

    a_list = app_client.get(f"/api/v1/catalog/materials/{material_a['id']}/thicknesses", headers=owner_headers).json()
    b_list = app_client.get(f"/api/v1/catalog/materials/{material_b['id']}/thicknesses", headers=owner_headers).json()
    assert [i["thickness_mm"] for i in a_list["items"]] == ["12"]
    assert [i["thickness_mm"] for i in b_list["items"]] == ["30"]


def test_delete_thickness(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    material = _create_material(app_client, owner_headers, brand["id"])
    thickness = app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/thicknesses",
        headers=owner_headers,
        json={"thickness_mm": "12"},
    ).json()

    resp = app_client.delete(f"/api/v1/catalog/material-thicknesses/{thickness['id']}", headers=owner_headers)
    assert resp.status_code == 204
    list_resp = app_client.get(f"/api/v1/catalog/materials/{material['id']}/thicknesses", headers=owner_headers)
    assert list_resp.json()["items"] == []


def test_add_and_list_sizes(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    material = _create_material(app_client, owner_headers, brand["id"])

    resp = app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/sizes",
        headers=owner_headers,
        json={"dimensions": "3200x1600mm", "sort_order": 1},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["dimensions"] == "3200x1600mm"

    list_resp = app_client.get(f"/api/v1/catalog/materials/{material['id']}/sizes", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 1


def test_delete_size(app_client, owner_headers):
    brand = _create_brand(app_client, owner_headers)
    material = _create_material(app_client, owner_headers, brand["id"])
    size = app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/sizes",
        headers=owner_headers,
        json={"dimensions": "3200x1600mm"},
    ).json()

    resp = app_client.delete(f"/api/v1/catalog/material-sizes/{size['id']}", headers=owner_headers)
    assert resp.status_code == 204
    list_resp = app_client.get(f"/api/v1/catalog/materials/{material['id']}/sizes", headers=owner_headers)
    assert list_resp.json()["items"] == []


def test_thickness_and_size_require_existing_material(app_client, owner_headers):
    import uuid

    resp = app_client.post(
        f"/api/v1/catalog/materials/{uuid.uuid4()}/thicknesses",
        headers=owner_headers,
        json={"thickness_mm": "12"},
    )
    assert resp.status_code == 404

    resp = app_client.post(
        f"/api/v1/catalog/materials/{uuid.uuid4()}/sizes",
        headers=owner_headers,
        json={"dimensions": "3200x1600mm"},
    )
    assert resp.status_code == 404


def test_thickness_and_size_write_audit_log(app_client, owner_headers, db_session):
    brand = _create_brand(app_client, owner_headers)
    material = _create_material(app_client, owner_headers, brand["id"])
    app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/thicknesses",
        headers=owner_headers,
        json={"thickness_mm": "12"},
    )
    app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/sizes",
        headers=owner_headers,
        json={"dimensions": "3200x1600mm"},
    )

    actions = [r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == "material").all()]
    assert "material.thickness_added" in actions
    assert "material.size_added" in actions
