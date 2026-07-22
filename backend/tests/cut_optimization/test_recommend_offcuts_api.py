"""API tests for Smart Offcut Management (Phase 2 requirement #2): search
existing offcuts first, rank candidates, explain the pick, and only
recommend a new slab purchase when nothing fits."""


def _piece(label="Countertop", length_mm="500", width_mm="400", quantity=1, allow_rotation=True):
    return {"label": label, "length_mm": length_mm, "width_mm": width_mm, "quantity": quantity, "allow_rotation": allow_rotation}


def _make_offcut(app_client, owner_headers, material, warehouse, slab_number, length_mm, width_mm):
    """An offcut must come from an in_production parent slab, per the
    Phase 1 offcut-registration rule -- exercised here rather than
    inserted directly, so this test also proves the two phases interoperate."""
    parent = app_client.post(
        "/api/v1/catalog/slabs",
        headers=owner_headers,
        json={"material_id": str(material.id), "warehouse_id": str(warehouse.id), "slab_number": f"PARENT-{slab_number}"},
    ).json()
    app_client.patch(f"/api/v1/catalog/slabs/{parent['id']}/status", headers=owner_headers, json={"status": "reserved"})
    app_client.patch(f"/api/v1/catalog/slabs/{parent['id']}/status", headers=owner_headers, json={"status": "in_production"})
    offcut = app_client.post(
        f"/api/v1/catalog/slabs/{parent['id']}/offcuts",
        headers=owner_headers,
        json={"warehouse_id": str(warehouse.id), "slab_number": slab_number, "length_mm": length_mm, "width_mm": width_mm},
    ).json()
    return offcut


def test_recommends_no_new_slab_when_no_offcuts_exist(app_client, owner_headers, material):
    resp = app_client.post(
        "/api/v1/cut_optimization/recommendations",
        headers=owner_headers,
        json={"material_id": str(material.id), "kerf_mm": "3", "pieces": [_piece()]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recommend_new_slab"] is True
    assert body["candidates"] == []
    assert body["persisted_run_id"] is None


def test_recommends_a_fitting_offcut_and_persists_it_as_a_run(app_client, owner_headers, material, warehouse):
    offcut = _make_offcut(app_client, owner_headers, material, warehouse, "OFFCUT-1", "800", "600")

    resp = app_client.post(
        "/api/v1/cut_optimization/recommendations",
        headers=owner_headers,
        json={"material_id": str(material.id), "kerf_mm": "3", "pieces": [_piece()]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recommend_new_slab"] is False
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["slab_id"] == offcut["id"]
    assert body["candidates"][0]["fits"] is True
    assert "Selected" in body["candidates"][0]["explanation"]
    assert body["persisted_run_id"] is not None

    history = app_client.get("/api/v1/cut_optimization/runs", headers=owner_headers).json()["items"]
    assert any(r["id"] == body["persisted_run_id"] for r in history)
    persisted = next(r for r in history if r["id"] == body["persisted_run_id"])
    assert persisted["source"] == "offcut_recommendation"
    assert persisted["slab_id"] == offcut["id"]


def test_ranks_the_least_wasteful_offcut_first(app_client, owner_headers, material, warehouse):
    # A much larger offcut fits the piece too, but wastes far more area --
    # the smaller, tighter-fitting offcut should rank first.
    tight_fit = _make_offcut(app_client, owner_headers, material, warehouse, "OFFCUT-TIGHT", "550", "450")
    _make_offcut(app_client, owner_headers, material, warehouse, "OFFCUT-LOOSE", "2000", "2000")

    resp = app_client.post(
        "/api/v1/cut_optimization/recommendations",
        headers=owner_headers,
        json={"material_id": str(material.id), "kerf_mm": "3", "pieces": [_piece()]},
    )
    body = resp.json()
    fitting = [c for c in body["candidates"] if c["fits"]]
    assert len(fitting) == 2
    assert fitting[0]["slab_id"] == tight_fit["id"]
    assert fitting[0]["utilization_pct"] > fitting[1]["utilization_pct"]


def test_offcut_too_small_is_not_recommended(app_client, owner_headers, material, warehouse):
    _make_offcut(app_client, owner_headers, material, warehouse, "OFFCUT-TINY", "100", "100")

    resp = app_client.post(
        "/api/v1/cut_optimization/recommendations",
        headers=owner_headers,
        json={"material_id": str(material.id), "kerf_mm": "3", "pieces": [_piece()]},
    )
    body = resp.json()
    assert body["recommend_new_slab"] is True
    assert body["candidates"][0]["fits"] is False


def test_recommendation_filters_by_thickness_and_finish(app_client, owner_headers, material, warehouse, db_session):
    from modules.catalog.infrastructure.models.material import StoneMaterial

    other_material = StoneMaterial(
        company_id=material.company_id, brand_id=material.brand_id, name="Different Spec",
        finish="Honed", thickness_mm="30",
    )
    db_session.add(other_material)
    db_session.commit()

    _make_offcut(app_client, owner_headers, material, warehouse, "OFFCUT-MATCH", "800", "600")
    parent2 = app_client.post(
        "/api/v1/catalog/slabs", headers=owner_headers,
        json={"material_id": str(other_material.id), "warehouse_id": str(warehouse.id), "slab_number": "PARENT-OTHER"},
    ).json()
    app_client.patch(f"/api/v1/catalog/slabs/{parent2['id']}/status", headers=owner_headers, json={"status": "reserved"})
    app_client.patch(f"/api/v1/catalog/slabs/{parent2['id']}/status", headers=owner_headers, json={"status": "in_production"})
    other_offcut = app_client.post(
        f"/api/v1/catalog/slabs/{parent2['id']}/offcuts", headers=owner_headers,
        json={"warehouse_id": str(warehouse.id), "slab_number": "OFFCUT-OTHER-SPEC", "length_mm": "800", "width_mm": "600"},
    ).json()

    resp = app_client.post(
        "/api/v1/cut_optimization/recommendations",
        headers=owner_headers,
        json={
            "material_id": str(other_material.id), "kerf_mm": "3", "pieces": [_piece()],
            "thickness_mm": "30", "finish": "Honed",
        },
    )
    body = resp.json()
    slab_ids = {c["slab_id"] for c in body["candidates"]}
    assert other_offcut["id"] in slab_ids


def test_recommendation_is_scoped_to_company(app_client, owner_headers, material, warehouse, db_session):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    _make_offcut(app_client, owner_headers, material, warehouse, "OFFCUT-A", "800", "600")

    other_company = Company(name="Other Co", slug="other-co-recommend", enabled_modules=["catalog", "cut_optimization"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="owner@other-recommend.test", password_hash=hash_password("Password123!"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_headers = {
        "Authorization": f"Bearer {create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)}"
    }

    resp = app_client.post(
        "/api/v1/cut_optimization/recommendations",
        headers=other_headers,
        json={"material_id": str(material.id), "kerf_mm": "3", "pieces": [_piece()]},
    )
    assert resp.json()["recommend_new_slab"] is True
    assert resp.json()["candidates"] == []
