"""Tests for configurable production stages (Phase 1: Stone Fabrication
Workflow, requirement #4)."""


def test_list_stages_seeds_stone_fabrication_defaults(app_client, owner_headers):
    resp = app_client.get("/api/v1/production/stages", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    names = [s["name"] for s in resp.json()["items"]]
    assert names == [
        "Measuring",
        "Design",
        "CNC",
        "Waterjet",
        "Cutting",
        "Polishing",
        "Quality Control",
        "Ready for Installation",
    ]


def test_list_stages_is_idempotent_after_seeding(app_client, owner_headers):
    first = app_client.get("/api/v1/production/stages", headers=owner_headers).json()["items"]
    second = app_client.get("/api/v1/production/stages", headers=owner_headers).json()["items"]
    assert [s["id"] for s in first] == [s["id"] for s in second]


def test_create_custom_stage(app_client, owner_headers):
    app_client.get("/api/v1/production/stages", headers=owner_headers)  # seed defaults first

    resp = app_client.post(
        "/api/v1/production/stages", headers=owner_headers, json={"name": "Edge Polishing"}
    )
    assert resp.status_code == 200, resp.text
    stage = resp.json()
    assert stage["name"] == "Edge Polishing"
    assert stage["sort_order"] == 8  # appended after the 8 seeded defaults

    listed = app_client.get("/api/v1/production/stages", headers=owner_headers).json()["items"]
    assert any(s["name"] == "Edge Polishing" for s in listed)


def test_rename_and_hide_stage(app_client, owner_headers):
    stages = app_client.get("/api/v1/production/stages", headers=owner_headers).json()["items"]
    stage_id = stages[0]["id"]

    resp = app_client.patch(
        f"/api/v1/production/stages/{stage_id}", headers=owner_headers, json={"name": "Measuring & Templating"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Measuring & Templating"

    hidden = app_client.patch(
        f"/api/v1/production/stages/{stage_id}", headers=owner_headers, json={"is_active": False}
    )
    assert hidden.status_code == 200
    assert hidden.json()["is_active"] is False


def test_stages_are_scoped_per_company(app_client, owner_headers, db_session):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    app_client.get("/api/v1/production/stages", headers=owner_headers)  # seed company A

    other_company = Company(name="Other Co", slug="other-co-stages", enabled_modules=["production"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="owner@other-stages.test", password_hash=hash_password("Password123!"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_headers = {
        "Authorization": f"Bearer {create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)}"
    }

    company_a_stages = app_client.get("/api/v1/production/stages", headers=owner_headers).json()["items"]
    company_b_stages = app_client.get("/api/v1/production/stages", headers=other_headers).json()["items"]

    # Independently seeded -- same default names, but disjoint ids/rows.
    assert len(company_a_stages) == len(company_b_stages) == 8
    assert {s["id"] for s in company_a_stages}.isdisjoint({s["id"] for s in company_b_stages})
