"""Covers RELEASE_CHECKLIST.md H5: assigned_manager_id must reference a real
member of the active company."""
import uuid


def test_create_customer_rejects_unknown_assigned_manager(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Bad Manager Co", "type": "business", "assigned_manager_id": str(uuid.uuid4())},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_customer_accepts_real_company_member_as_manager(app_client, owner_headers, owner_user):
    response = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Good Manager Co", "type": "business", "assigned_manager_id": str(owner_user.id)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["assigned_manager_id"] == str(owner_user.id)


def test_update_customer_rejects_unknown_assigned_manager(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Update Target Co", "type": "business"}
    ).json()

    response = app_client.patch(
        f"/api/v1/crm/customers/{created['id']}",
        headers=owner_headers,
        json={"assigned_manager_id": str(uuid.uuid4())},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_customer_accepts_real_company_member_as_manager(app_client, owner_headers, owner_user):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Update Target Co 2", "type": "business"}
    ).json()

    response = app_client.patch(
        f"/api/v1/crm/customers/{created['id']}",
        headers=owner_headers,
        json={"assigned_manager_id": str(owner_user.id)},
    )
    assert response.status_code == 200
    assert response.json()["assigned_manager_id"] == str(owner_user.id)


def test_assigned_manager_from_another_company_is_rejected(app_client, owner_headers, db_session):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import hash_password
    from core.companies.models import Company

    other_company = Company(name="Other Co", slug="other-co-mgr-test", enabled_modules=["crm"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="outsider@test.example", password_hash=hash_password("x"), full_name="Outsider")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()

    response = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Cross Tenant Co", "type": "business", "assigned_manager_id": str(other_user.id)},
    )
    assert response.status_code == 400
