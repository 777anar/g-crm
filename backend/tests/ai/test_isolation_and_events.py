"""Multi-company isolation for the AI Sales Assistant module."""


def test_recommendations_isolated_by_company(app_client, db_session, owner_headers, lead, company):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    created = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    rec_id = created[0]["id"]

    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-ai-test", enabled_modules=["ai"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@ai.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = app_client.get(f"/api/v1/ai/recommendations/{rec_id}", headers=other_headers)
    assert response.status_code == 404

    other_company_recs = app_client.get("/api/v1/ai/recommendations", headers=other_headers).json()
    assert rec_id not in [r["id"] for r in other_company_recs["items"]]

    other_dashboard = app_client.get("/api/v1/ai/dashboard", headers=other_headers).json()
    assert other_dashboard["usage_stats"]["total_recommendations"] == 0


def test_cannot_analyze_lead_belonging_to_another_company(app_client, db_session, owner_headers, lead):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    other_company = Company(name="NEOLITH BAKU", slug="neolith-baku-ai-test", enabled_modules=["ai", "crm"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner-2@ai.test", password_hash=hash_password("x"), full_name="Other Owner 2")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    resp = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=other_headers, json={})
    assert resp.status_code == 404
