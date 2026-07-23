"""Phase 18 (Security & Compliance Hardening): httpOnly-cookie auth, staff
TOTP MFA, and the compliance audit-log export/retention admin surface."""
import pyotp
import pytest

from core.auth.models import ROLE_OWNER, User, UserCompanyRole
from core.auth.security import ACCESS_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME, hash_password
from core.companies.models import Company


@pytest.fixture()
def company(db_session):
    company = Company(name="G-STONE GALLERY", slug="g-stone-gallery-p18", enabled_modules=["crm"])
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="p18-owner@test.example", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


def _login(app_client, email="p18-owner@test.example", password="Password123!"):
    return app_client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ── httpOnly cookie auth ─────────────────────────────────────────────────────


def test_login_sets_httponly_access_and_refresh_cookies(app_client, owner_user):
    resp = _login(app_client)
    assert resp.status_code == 200, resp.text
    assert ACCESS_TOKEN_COOKIE_NAME in resp.cookies
    assert REFRESH_TOKEN_COOKIE_NAME in resp.cookies
    # Body still carries the tokens too, for Bearer-token API clients.
    assert resp.json()["access_token"]
    assert resp.json()["refresh_token"]


def test_me_endpoint_authenticates_via_cookie_alone_no_header(app_client, owner_user, company):
    _login(app_client)
    select = app_client.post("/api/v1/auth/select-company", json={"company_id": str(company.id)})
    assert select.status_code == 200, select.text

    # No Authorization header at all -- TestClient's cookie jar carries the
    # access-token cookie set by login/select-company automatically.
    resp = app_client.get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "p18-owner@test.example"


def test_select_company_response_includes_role_and_permissions_claims(app_client, owner_user, company):
    _login(app_client)
    resp = app_client.post("/api/v1/auth/select-company", json={"company_id": str(company.id)})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == ROLE_OWNER
    assert body["active_company_id"] == str(company.id)
    assert isinstance(body["module_permissions"], dict)


def test_refresh_works_from_cookie_with_no_request_body(app_client, owner_user):
    _login(app_client)
    resp = app_client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_logout_clears_cookies_and_revokes_refresh_token(app_client, owner_user):
    login = _login(app_client).json()
    logout = app_client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert app_client.cookies.get(ACCESS_TOKEN_COOKIE_NAME) is None

    refresh_after = app_client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert refresh_after.status_code == 401


# ── Staff TOTP MFA ───────────────────────────────────────────────────────────


def test_mfa_setup_enable_then_login_requires_code(app_client, owner_user, company):
    _login(app_client)
    setup = app_client.post("/api/v1/auth/mfa/setup")
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://")

    code = pyotp.TOTP(secret).now()
    enable = app_client.post("/api/v1/auth/mfa/enable", json={"code": code})
    assert enable.status_code == 200, enable.text
    assert enable.json()["mfa_enabled"] is True

    app_client.post("/api/v1/auth/logout")

    login = _login(app_client)
    assert login.status_code == 200
    body = login.json()
    assert body["mfa_required"] is True
    assert body["mfa_token"]
    assert not body["access_token"]

    verify = app_client.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": body["mfa_token"], "code": pyotp.TOTP(secret).now()}
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["access_token"]


def test_mfa_verify_rejects_wrong_code(app_client, owner_user):
    _login(app_client)
    setup = app_client.post("/api/v1/auth/mfa/setup").json()
    app_client.post("/api/v1/auth/mfa/enable", json={"code": pyotp.TOTP(setup["secret"]).now()})
    app_client.post("/api/v1/auth/logout")

    login = _login(app_client).json()
    resp = app_client.post("/api/v1/auth/mfa/verify", json={"mfa_token": login["mfa_token"], "code": "000000"})
    assert resp.status_code == 401


def test_mfa_disable_requires_a_valid_code(app_client, owner_user):
    _login(app_client)
    setup = app_client.post("/api/v1/auth/mfa/setup").json()
    app_client.post("/api/v1/auth/mfa/enable", json={"code": pyotp.TOTP(setup["secret"]).now()})

    bad = app_client.post("/api/v1/auth/mfa/disable", json={"code": "000000"})
    assert bad.status_code == 401

    good = app_client.post("/api/v1/auth/mfa/disable", json={"code": pyotp.TOTP(setup["secret"]).now()})
    assert good.status_code == 200
    assert good.json()["mfa_enabled"] is False


def test_select_company_blocked_when_company_requires_mfa_for_role(app_client, db_session, owner_user, company):
    company.mfa_required_roles = [ROLE_OWNER]
    db_session.add(company)
    db_session.commit()

    _login(app_client)
    resp = app_client.post("/api/v1/auth/select-company", json={"company_id": str(company.id)})
    assert resp.status_code == 403
    assert "MFA" in resp.json()["error"]["message"]


def test_select_company_succeeds_once_mfa_enabled_for_required_role(app_client, db_session, owner_user, company):
    company.mfa_required_roles = [ROLE_OWNER]
    db_session.add(company)
    db_session.commit()

    _login(app_client)
    setup = app_client.post("/api/v1/auth/mfa/setup").json()
    app_client.post("/api/v1/auth/mfa/enable", json={"code": pyotp.TOTP(setup["secret"]).now()})

    resp = app_client.post("/api/v1/auth/select-company", json={"company_id": str(company.id)})
    assert resp.status_code == 200, resp.text


# ── Compliance audit-log export/retention admin surface ────────────────────


@pytest.fixture()
def selected_owner(app_client, owner_user, company):
    """Logs the owner in and selects `company` so the client's cookie jar
    carries a company-scoped access token for the rest of the test."""
    _login(app_client)
    app_client.post("/api/v1/auth/select-company", json={"company_id": str(company.id)})
    return owner_user


def test_audit_log_export_surface_lists_entries_created_by_a_real_write(app_client, selected_owner, company):
    # Any audited write produces an audit_log row -- creating a customer is
    # the simplest one available without pulling in another module's fixtures.
    create = app_client.post(
        "/api/v1/crm/customers",
        json={"name": "Audit Test Customer", "type": "individual", "status": "new_inquiry"},
    )
    assert create.status_code == 200, create.text

    listing = app_client.get("/api/v1/audit/logs")
    assert listing.status_code == 200, listing.text
    items = listing.json()["items"]
    assert any(item["entity_type"] == "customer" and item["module"] == "crm" for item in items)

    export = app_client.get("/api/v1/audit/logs/export")
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "customer" in export.text


def test_retention_policy_defaults_to_none_then_can_be_set(app_client, selected_owner):
    get_resp = app_client.get("/api/v1/audit/retention-policy")
    assert get_resp.status_code == 200
    assert get_resp.json()["retention_days"] is None

    put_resp = app_client.put("/api/v1/audit/retention-policy", json={"retention_days": 30})
    assert put_resp.status_code == 200
    assert put_resp.json()["retention_days"] == 30

    get_again = app_client.get("/api/v1/audit/retention-policy")
    assert get_again.json()["retention_days"] == 30


def test_purge_without_a_configured_policy_is_rejected(app_client, selected_owner):
    resp = app_client.post("/api/v1/audit/retention-policy/purge")
    assert resp.status_code == 422


def test_purge_deletes_only_entries_older_than_the_retention_window(app_client, db_session, selected_owner, company):
    import uuid
    from datetime import datetime, timedelta, timezone

    from core.audit.models import AuditLog

    old_entry = AuditLog(
        company_id=company.id,
        module="crm",
        actor_user_id=selected_owner.id,
        action="create",
        entity_type="customer",
        entity_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc) - timedelta(days=400),
    )
    recent_entry = AuditLog(
        company_id=company.id,
        module="crm",
        actor_user_id=selected_owner.id,
        action="create",
        entity_type="customer",
        entity_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([old_entry, recent_entry])
    db_session.commit()

    app_client.put("/api/v1/audit/retention-policy", json={"retention_days": 90})
    purge = app_client.post("/api/v1/audit/retention-policy/purge")
    assert purge.status_code == 200, purge.text
    assert purge.json()["deleted_count"] == 1

    remaining = db_session.query(AuditLog).filter(AuditLog.company_id == company.id).all()
    assert len(remaining) == 1
    assert remaining[0].id == recent_entry.id


def test_audit_surface_requires_owner_permission(app_client, db_session, company):
    from core.auth.models import ROLE_VIEWER

    viewer = User(email="p18-viewer@test.example", password_hash=hash_password("Password123!"), full_name="Viewer")
    db_session.add(viewer)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=viewer.id, company_id=company.id, role=ROLE_VIEWER))
    db_session.commit()

    _login(app_client, email="p18-viewer@test.example")
    app_client.post("/api/v1/auth/select-company", json={"company_id": str(company.id)})

    resp = app_client.get("/api/v1/audit/logs")
    assert resp.status_code == 403


# ── CORS configuration ──────────────────────────────────────────────────────


def test_cors_no_longer_wildcards_methods_or_headers():
    from core.config import settings

    assert "*" not in settings.cors_allow_methods
    assert "*" not in settings.cors_allow_headers
    assert "POST" in settings.cors_allow_methods
    assert "Authorization" in settings.cors_allow_headers
