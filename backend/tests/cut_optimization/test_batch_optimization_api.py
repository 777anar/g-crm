"""API tests for multi-slab / cross-job batch optimization and CNC/DXF
export (Phase 20: Advanced Cut Optimization & Supply Chain Intelligence)."""
import uuid


def _piece(label="Countertop", length_mm="2000", width_mm="800", quantity=1, allow_rotation=True):
    return {"label": label, "length_mm": length_mm, "width_mm": width_mm, "quantity": quantity, "allow_rotation": allow_rotation}


def _make_available_slab(app_client, owner_headers, material, warehouse, slab_number, length_mm, width_mm):
    return app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={
            "material_id": str(material.id), "warehouse_id": str(warehouse.id), "slab_number": slab_number,
            "length_mm": length_mm, "width_mm": width_mm,
        },
    ).json()


def test_batch_run_explicit_slab_ids_nests_across_both_slabs(app_client, owner_headers, material, warehouse):
    slab_a = _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-A", "1000", "1000")
    slab_b = _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-B", "1000", "1000")

    resp = app_client.post(
        "/api/v1/cut_optimization/batch-runs",
        headers=owner_headers,
        json={
            "material_id": str(material.id),
            "kerf_mm": "0",
            "slab_ids": [slab_a["id"], slab_b["id"]],
            "pieces": [
                _piece(label="WO-1: Piece A", length_mm="900", width_mm="900", quantity=1, allow_rotation=False),
                _piece(label="WO-2: Piece B", length_mm="900", width_mm="900", quantity=1, allow_rotation=False),
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slabs_used_count"] == 2
    assert body["unplaced"] == []
    assert len(body["placements"]) == 2
    assert float(body["utilization_pct"]) > 0


def test_batch_run_auto_selects_smallest_available_slabs_first(app_client, owner_headers, material, warehouse):
    _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-SMALL", "1000", "1000")
    _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-LARGE", "3200", "1600")

    resp = app_client.post(
        "/api/v1/cut_optimization/batch-runs",
        headers=owner_headers,
        json={
            "material_id": str(material.id),
            "kerf_mm": "0",
            "pieces": [_piece(length_mm="900", width_mm="900", allow_rotation=False)],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slabs_used_count"] == 1
    assert body["slabs"][0]["slab_ref"] == "BATCH-SMALL"


def test_batch_run_reports_unplaced_when_pieces_exceed_all_slabs(app_client, owner_headers, material, warehouse):
    slab = _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-TINY", "500", "500")

    resp = app_client.post(
        "/api/v1/cut_optimization/batch-runs",
        headers=owner_headers,
        json={
            "material_id": str(material.id),
            "kerf_mm": "0",
            "slab_ids": [slab["id"]],
            "pieces": [_piece(length_mm="5000", width_mm="5000", allow_rotation=False)],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slabs_used_count"] == 0
    assert len(body["unplaced"]) == 1


def test_batch_run_without_any_available_slabs_returns_422(app_client, owner_headers, material):
    resp = app_client.post(
        "/api/v1/cut_optimization/batch-runs",
        headers=owner_headers,
        json={"material_id": str(material.id), "kerf_mm": "3", "pieces": [_piece()]},
    )
    assert resp.status_code == 422, resp.text


def test_batch_run_requires_at_least_one_piece(app_client, owner_headers, material, warehouse):
    slab = _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-EMPTY", "1000", "1000")
    resp = app_client.post(
        "/api/v1/cut_optimization/batch-runs",
        headers=owner_headers,
        json={"material_id": str(material.id), "kerf_mm": "3", "slab_ids": [slab["id"]], "pieces": []},
    )
    assert resp.status_code == 422, resp.text


def test_list_and_reopen_batch_run_history(app_client, owner_headers, material, warehouse):
    slab = _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-HIST", "1000", "1000")
    created = app_client.post(
        "/api/v1/cut_optimization/batch-runs",
        headers=owner_headers,
        json={
            "material_id": str(material.id), "kerf_mm": "0", "slab_ids": [slab["id"]],
            "pieces": [_piece(length_mm="900", width_mm="900", allow_rotation=False)],
        },
    ).json()

    listed = app_client.get("/api/v1/cut_optimization/batch-runs", headers=owner_headers)
    assert listed.status_code == 200
    assert any(r["id"] == created["id"] for r in listed.json()["items"])

    reopened = app_client.get(f"/api/v1/cut_optimization/batch-runs/{created['id']}", headers=owner_headers)
    assert reopened.status_code == 200
    assert reopened.json()["placements"] == created["placements"]


def test_reopen_unknown_batch_run_returns_404(app_client, owner_headers):
    resp = app_client.get(f"/api/v1/cut_optimization/batch-runs/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


def test_batch_run_history_is_scoped_to_company(app_client, owner_headers, material, warehouse, db_session):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    slab = _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-SCOPE", "1000", "1000")
    created = app_client.post(
        "/api/v1/cut_optimization/batch-runs",
        headers=owner_headers,
        json={
            "material_id": str(material.id), "kerf_mm": "0", "slab_ids": [slab["id"]],
            "pieces": [_piece(length_mm="900", width_mm="900", allow_rotation=False)],
        },
    ).json()

    other_company = Company(name="Other Co", slug="other-co-batch", enabled_modules=["catalog", "cut_optimization"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="owner@other-batch.test", password_hash=hash_password("Password123!"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_headers = {
        "Authorization": f"Bearer {create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)}"
    }

    cross_company = app_client.get(f"/api/v1/cut_optimization/batch-runs/{created['id']}", headers=other_headers)
    assert cross_company.status_code == 404


def test_export_single_slab_run_as_dxf(app_client, owner_headers):
    run = app_client.post(
        "/api/v1/cut_optimization/runs",
        headers=owner_headers,
        json={"slab_length_mm": "3200", "slab_width_mm": "1600", "kerf_mm": "3", "pieces": [_piece()]},
    ).json()

    resp = app_client.get(f"/api/v1/cut_optimization/runs/{run['id']}/export.dxf", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/dxf"
    assert b"SECTION" in resp.content
    assert b"ENTITIES" in resp.content


def test_export_unknown_run_dxf_returns_404(app_client, owner_headers):
    resp = app_client.get(f"/api/v1/cut_optimization/runs/{uuid.uuid4()}/export.dxf", headers=owner_headers)
    assert resp.status_code == 404


def test_export_batch_run_as_dxf(app_client, owner_headers, material, warehouse):
    slab = _make_available_slab(app_client, owner_headers, material, warehouse, "BATCH-DXF", "1000", "1000")
    run = app_client.post(
        "/api/v1/cut_optimization/batch-runs",
        headers=owner_headers,
        json={
            "material_id": str(material.id), "kerf_mm": "0", "slab_ids": [slab["id"]],
            "pieces": [_piece(length_mm="900", width_mm="900", allow_rotation=False)],
        },
    ).json()

    resp = app_client.get(f"/api/v1/cut_optimization/batch-runs/{run['id']}/export.dxf", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/dxf"
    assert b"BATCH-DXF" in resp.content
