"""Staff-facing portal-access management: enabling/disabling a customer's
portal login, and resetting their password. All of these are audited
business writes (core.audit.service.record_audit + a domain event), unlike
the customer-facing login/refresh/logout in test_auth.py."""
import uuid


def test_enable_portal_access_success(app_client, owner_headers, customer, portal_credentials):
    resp = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access",
        headers=owner_headers,
        json=portal_credentials,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["customer_id"] == str(customer.id)
    assert body["email"] == portal_credentials["email"]
    assert body["is_active"] is True
    assert body["last_login_at"] is None


def test_enable_portal_access_requires_write_permission(app_client, viewer_headers, customer, portal_credentials):
    resp = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access",
        headers=viewer_headers,
        json=portal_credentials,
    )
    assert resp.status_code == 403


def test_enable_portal_access_unknown_customer_404(app_client, owner_headers, portal_credentials):
    resp = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{uuid.uuid4()}/access",
        headers=owner_headers,
        json=portal_credentials,
    )
    assert resp.status_code == 404


def test_enable_portal_access_twice_conflicts(app_client, owner_headers, customer, portal_credentials):
    first = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access",
        headers=owner_headers,
        json=portal_credentials,
    )
    assert first.status_code == 200, first.text

    second = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access",
        headers=owner_headers,
        json={"email": "different@portal.test", "password": "AnotherPass123!"},
    )
    assert second.status_code == 409


def test_enable_portal_access_duplicate_email_conflicts(app_client, db_session, owner_headers, company, portal_credentials):
    from modules.crm.infrastructure.models.customer import Customer

    other_customer = Customer(company_id=company.id, name="Second Customer", status="approved", type="individual")
    db_session.add(other_customer)
    db_session.commit()

    first = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{other_customer.id}/access",
        headers=owner_headers,
        json=portal_credentials,
    )
    assert first.status_code == 200, first.text

    # A second, different customer trying to reuse the same email.
    second_customer = Customer(company_id=company.id, name="Third Customer", status="approved", type="individual")
    db_session.add(second_customer)
    db_session.commit()

    second = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{second_customer.id}/access",
        headers=owner_headers,
        json=portal_credentials,
    )
    assert second.status_code == 409


def test_get_portal_access_not_enabled_404(app_client, owner_headers, customer):
    resp = app_client.get(f"/api/v1/customer_portal/admin/customers/{customer.id}/access", headers=owner_headers)
    assert resp.status_code == 404


def test_get_portal_access_success(app_client, owner_headers, customer, portal_access):
    resp = app_client.get(f"/api/v1/customer_portal/admin/customers/{customer.id}/access", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["customer_id"] == str(customer.id)


def test_reset_password_not_enabled_404(app_client, owner_headers, customer):
    resp = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access/reset-password",
        headers=owner_headers,
        json={"password": "NewPassword123!"},
    )
    assert resp.status_code == 404


def test_reset_password_then_old_password_fails_new_succeeds(
    app_client, owner_headers, customer, portal_access, portal_credentials
):
    new_password = "BrandNewPassword123!"
    reset = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access/reset-password",
        headers=owner_headers,
        json={"password": new_password},
    )
    assert reset.status_code == 200, reset.text

    old_login = app_client.post("/api/v1/customer_portal/auth/login", json=portal_credentials)
    assert old_login.status_code == 401

    new_login = app_client.post(
        "/api/v1/customer_portal/auth/login",
        json={"email": portal_credentials["email"], "password": new_password},
    )
    assert new_login.status_code == 200, new_login.text


def test_set_active_false_disables_login(app_client, owner_headers, customer, portal_access, portal_credentials):
    disable = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access/status",
        headers=owner_headers,
        json={"is_active": False},
    )
    assert disable.status_code == 200, disable.text
    assert disable.json()["is_active"] is False

    login = app_client.post("/api/v1/customer_portal/auth/login", json=portal_credentials)
    assert login.status_code == 401

    enable = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access/status",
        headers=owner_headers,
        json={"is_active": True},
    )
    assert enable.status_code == 200, enable.text

    login_again = app_client.post("/api/v1/customer_portal/auth/login", json=portal_credentials)
    assert login_again.status_code == 200, login_again.text


def test_set_active_not_enabled_404(app_client, owner_headers, customer):
    resp = app_client.post(
        f"/api/v1/customer_portal/admin/customers/{customer.id}/access/status",
        headers=owner_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 404
