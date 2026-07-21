"""Multi-company isolation and audit/event verification for the Marketing
module. Isolation matters especially here: campaign performance reads
crm_leads/orders directly (a cross-module read, not a query against
Marketing's own tables), so it must never leak another company's leads or
revenue into a campaign's numbers -- even if, hypothetically, two companies
used the same campaign_id by coincidence, which the company_id filter on
every query must prevent."""


def test_campaigns_are_isolated_by_company(app_client, db_session, owner_headers, campaign):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    other_company = Company(
        name="KORONA PREMIUM", slug="korona-premium-marketing-test", enabled_modules=["marketing"]
    )
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@marketing.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = app_client.get(f"/api/v1/marketing/campaigns/{campaign['id']}", headers=other_headers)
    assert response.status_code == 404

    other_list = app_client.get("/api/v1/marketing/campaigns", headers=other_headers).json()
    assert campaign["id"] not in [c["id"] for c in other_list["items"]]

    # Even a request for (by sheer coincidence) the same campaign id from
    # another company must 404, not silently compute performance against it.
    perf_response = app_client.get(f"/api/v1/marketing/campaigns/{campaign['id']}/performance", headers=other_headers)
    assert perf_response.status_code == 404


def test_performance_never_counts_another_companys_leads(app_client, db_session, owner_headers, company, campaign):
    """A lead in a different company that happens to carry the exact same
    campaign_id UUID (only possible in this test because we force it via
    direct DB access) must never be counted -- proves the performance query
    is company_id-scoped, not just campaign_id-scoped."""
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company
    from modules.crm.infrastructure.models.lead import Lead

    other_company = Company(
        name="NEOLITH BAKU", slug="neolith-baku-marketing-test", enabled_modules=["crm", "marketing"]
    )
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner-2@marketing.test", password_hash=hash_password("x"), full_name="Other Owner 2")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))

    # A lead in the OTHER company, deliberately carrying this company's
    # campaign id (an id collision that could only happen via direct DB
    # manipulation like this, but the query must still be safe against it).
    db_session.add(
        Lead(
            company_id=other_company.id,
            full_name="Cross-Tenant Lead",
            source_channel="instagram",
            campaign_id=campaign["id"],
        )
    )
    db_session.commit()

    resp = app_client.get(f"/api/v1/marketing/campaigns/{campaign['id']}/performance", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["leads_count"] == 0


def test_campaign_creation_writes_audit_and_event(app_client, owner_headers, db_session, owner_user, company):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(
        "/api/v1/marketing/campaigns", headers=owner_headers, json={"name": "Google Ads", "channel": "website"}
    )

    entry = db_session.query(AuditLog).filter(AuditLog.action == "campaign.created").first()
    assert entry is not None
    assert entry.actor_user_id == owner_user.id
    assert entry.company_id == company.id
    assert entry.module == "marketing"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "CampaignCreated" in events


def test_campaign_status_change_writes_audit_and_event(app_client, owner_headers, db_session, campaign):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(
        f"/api/v1/marketing/campaigns/{campaign['id']}/status", headers=owner_headers, json={"status": "active"}
    )

    actions = [r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == "campaign").all()]
    assert "campaign.status_changed" in actions

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "CampaignStatusChanged" in events
