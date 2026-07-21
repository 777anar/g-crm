"""Customer login/refresh/logout -- a deliberately separate identity from
staff auth (core/auth). The cross-token tests below prove a staff access
token and a customer access token are never interchangeable, which is the
whole point of giving them distinct JWT `type` claims."""


def test_login_success_returns_tokens(app_client, portal_access, portal_credentials):
    resp = app_client.post("/api/v1/customer_portal/auth/login", json=portal_credentials)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password_401(app_client, portal_access, portal_credentials):
    resp = app_client.post(
        "/api/v1/customer_portal/auth/login",
        json={"email": portal_credentials["email"], "password": "WrongPassword!"},
    )
    assert resp.status_code == 401


def test_login_unknown_email_401(app_client):
    resp = app_client.post(
        "/api/v1/customer_portal/auth/login", json={"email": "nobody@nowhere.test", "password": "whatever"}
    )
    assert resp.status_code == 401


def test_a_staff_access_token_is_rejected_by_the_portal_me_endpoint(app_client, owner_headers):
    resp = app_client.get("/api/v1/customer_portal/me", headers=owner_headers)
    assert resp.status_code == 401


def test_a_portal_access_token_is_rejected_by_a_staff_endpoint(app_client, portal_headers):
    resp = app_client.get("/api/v1/crm/customers", headers=portal_headers)
    assert resp.status_code == 401


def test_refresh_issues_a_new_access_token(app_client, portal_access, portal_credentials):
    login = app_client.post("/api/v1/customer_portal/auth/login", json=portal_credentials).json()
    resp = app_client.post("/api/v1/customer_portal/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_refresh_with_a_staff_refresh_token_is_rejected(app_client, owner_user, company):
    from core.auth.security import create_refresh_token

    staff_refresh = create_refresh_token(user_id=owner_user.id, generation=0)
    resp = app_client.post("/api/v1/customer_portal/auth/refresh", json={"refresh_token": staff_refresh})
    assert resp.status_code == 401


def test_logout_revokes_the_refresh_token(app_client, portal_access, portal_credentials):
    login = app_client.post("/api/v1/customer_portal/auth/login", json=portal_credentials).json()

    logout = app_client.post("/api/v1/customer_portal/auth/logout", json={"refresh_token": login["refresh_token"]})
    assert logout.status_code == 200

    refresh_after_logout = app_client.post(
        "/api/v1/customer_portal/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert refresh_after_logout.status_code == 401


def test_logout_with_garbage_token_does_not_error(app_client):
    resp = app_client.post("/api/v1/customer_portal/auth/logout", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 200
