"""Tests for Phase 21's cost-control layer: per-company rate limiting,
the daily spend budget cap, and the `AIProviderCallLog` audit trail /
`GET /ai/usage` visibility endpoint both are built on."""
from decimal import Decimal

from core.config import settings
from modules.ai.infrastructure.models.provider_call_log import AIProviderCallLog
from modules.ai.infrastructure.rate_limit import ai_analysis_rate_limiter


def test_usage_endpoint_is_empty_for_a_fresh_company(app_client, owner_headers):
    resp = app_client.get("/api/v1/ai/usage", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["calls_today"] == 0
    assert body["spent_today_usd"] == "0"
    assert body["recent_calls"] == []


def test_successful_mock_analysis_is_logged(app_client, owner_headers, lead, db_session):
    resp = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 200, resp.text

    logs = db_session.query(AIProviderCallLog).all()
    assert len(logs) == 1
    assert logs[0].success is True
    assert logs[0].provider == "mock"

    usage = app_client.get("/api/v1/ai/usage", headers=owner_headers).json()
    assert usage["calls_today"] == 1
    assert usage["recent_calls"][0]["provider"] == "mock"
    assert usage["recent_calls"][0]["success"] is True


def test_analyzing_with_unconfigured_anthropic_provider_returns_503_and_logs_failure(app_client, owner_headers, lead, db_session):
    resp = app_client.post(
        f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={"provider": "anthropic"}
    )
    assert resp.status_code == 503, resp.text

    logs = db_session.query(AIProviderCallLog).all()
    assert len(logs) == 1
    assert logs[0].success is False
    assert logs[0].provider == "anthropic"
    assert "ANTHROPIC_API_KEY" in logs[0].error_message


def test_rate_limit_rejects_requests_beyond_the_per_company_window(app_client, owner_headers, lead, monkeypatch):
    monkeypatch.setattr(ai_analysis_rate_limiter, "max_requests", 2)

    first = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    second = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    third = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert third.status_code == 429, third.text


def test_rate_limit_is_scoped_per_company(app_client, owner_headers, lead, monkeypatch, db_session):
    """A different company's calls don't count against this company's window."""
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    monkeypatch.setattr(ai_analysis_rate_limiter, "max_requests", 1)

    other_company = Company(name="Other AI Co", slug="other-ai-co", enabled_modules=["crm", "ai"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="owner@other-ai.test", password_hash=hash_password("Password123!"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_headers = {
        "Authorization": f"Bearer {create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)}"
    }

    first = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    assert first.status_code == 200, first.text

    other_lead = app_client.post(
        "/api/v1/crm/leads", headers=other_headers,
        json={"full_name": "Other Lead", "source_channel": "website"},
    ).json()
    other_resp = app_client.post(f"/api/v1/ai/leads/{other_lead['id']}/analyze", headers=other_headers, json={})
    assert other_resp.status_code == 200, other_resp.text


def test_daily_budget_cap_rejects_further_calls_once_reached(app_client, owner_headers, lead, monkeypatch, db_session, company):
    monkeypatch.setattr(settings, "ai_daily_budget_usd", 1.0)
    db_session.add(AIProviderCallLog(
        company_id=company.id, analysis_kind="lead", provider="anthropic", model="claude-opus-4-8",
        prompt="prior call", cost_usd=Decimal("1.50"), latency_ms=100, success=True,
    ))
    db_session.commit()

    resp = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 429, resp.text


def test_daily_budget_of_zero_disables_the_cap(app_client, owner_headers, lead, monkeypatch, db_session, company):
    monkeypatch.setattr(settings, "ai_daily_budget_usd", 0)
    db_session.add(AIProviderCallLog(
        company_id=company.id, analysis_kind="lead", provider="anthropic", model="claude-opus-4-8",
        prompt="prior call", cost_usd=Decimal("999.00"), latency_ms=100, success=True,
    ))
    db_session.commit()

    resp = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 200, resp.text


def test_usage_is_readable_by_viewer_tier(app_client, viewer_headers):
    """`ai:dashboard:read` is a viewer-tier permission (same as the AI
    Dashboard it's reused from) -- consistent with this codebase's `:read`
    == viewer / `:write` == rep RBAC convention."""
    resp = app_client.get("/api/v1/ai/usage", headers=viewer_headers)
    assert resp.status_code == 200
