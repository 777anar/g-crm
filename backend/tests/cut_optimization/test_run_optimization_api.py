"""API tests for the Cut Optimization run/history surface (Phase 2
requirements #1 and #4)."""
import uuid


def _piece(label="Countertop", length_mm="2000", width_mm="800", quantity=1, allow_rotation=True):
    return {"label": label, "length_mm": length_mm, "width_mm": width_mm, "quantity": quantity, "allow_rotation": allow_rotation}


def test_run_against_raw_slab_dimensions(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/cut_optimization/runs",
        headers=owner_headers,
        json={
            "slab_length_mm": "3200",
            "slab_width_mm": "1600",
            "kerf_mm": "3",
            "pieces": [_piece()],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "manual"
    assert len(body["placements"]) == 1
    assert body["unplaced"] == []
    assert float(body["utilization_pct"]) > 0


def test_run_against_a_real_slab_id(app_client, owner_headers, material, warehouse):
    slab = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={
            "material_id": str(material.id), "warehouse_id": str(warehouse.id), "slab_number": "SL-CO-001",
            "length_mm": "3200", "width_mm": "1600",
        },
    ).json()

    resp = app_client.post(
        "/api/v1/cut_optimization/runs",
        headers=owner_headers,
        json={"slab_id": slab["id"], "kerf_mm": "3", "pieces": [_piece()]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slab_id"] == slab["id"]
    assert body["material_id"] == str(material.id)


def test_run_requires_slab_id_or_explicit_dimensions(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/cut_optimization/runs",
        headers=owner_headers,
        json={"kerf_mm": "3", "pieces": [_piece()]},
    )
    assert resp.status_code == 422, resp.text


def test_run_reports_unplaced_pieces_that_do_not_fit(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/cut_optimization/runs",
        headers=owner_headers,
        json={
            "slab_length_mm": "1000", "slab_width_mm": "1000", "kerf_mm": "0",
            "pieces": [_piece(length_mm="5000", width_mm="5000", allow_rotation=False)],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["placements"] == []
    assert len(body["unplaced"]) == 1


def test_unknown_slab_id_returns_404(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/cut_optimization/runs",
        headers=owner_headers,
        json={"slab_id": str(uuid.uuid4()), "kerf_mm": "3", "pieces": [_piece()]},
    )
    assert resp.status_code == 404


def test_list_and_reopen_optimization_history(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/cut_optimization/runs",
        headers=owner_headers,
        json={"slab_length_mm": "3200", "slab_width_mm": "1600", "kerf_mm": "3", "pieces": [_piece()]},
    ).json()

    listed = app_client.get("/api/v1/cut_optimization/runs", headers=owner_headers)
    assert listed.status_code == 200
    assert any(r["id"] == created["id"] for r in listed.json()["items"])

    reopened = app_client.get(f"/api/v1/cut_optimization/runs/{created['id']}", headers=owner_headers)
    assert reopened.status_code == 200
    assert reopened.json()["placements"] == created["placements"]


def test_reopen_unknown_run_returns_404(app_client, owner_headers):
    resp = app_client.get(f"/api/v1/cut_optimization/runs/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


def test_history_is_scoped_to_company(app_client, owner_headers, db_session):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    created = app_client.post(
        "/api/v1/cut_optimization/runs",
        headers=owner_headers,
        json={"slab_length_mm": "3200", "slab_width_mm": "1600", "kerf_mm": "3", "pieces": [_piece()]},
    ).json()

    other_company = Company(name="Other Co", slug="other-co-cut-opt", enabled_modules=["cut_optimization"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="owner@other-cutopt.test", password_hash=hash_password("Password123!"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_headers = {
        "Authorization": f"Bearer {create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)}"
    }

    cross_company = app_client.get(f"/api/v1/cut_optimization/runs/{created['id']}", headers=other_headers)
    assert cross_company.status_code == 404

    other_list = app_client.get("/api/v1/cut_optimization/runs", headers=other_headers)
    assert other_list.json()["items"] == []
