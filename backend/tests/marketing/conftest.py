import pytest

from core.auth.models import ROLE_OWNER, ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE MARKETING TEST",
        slug="g-stone-marketing-test",
        enabled_modules=["crm", "catalog", "sales", "orders", "marketing"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="owner@marketing.test", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(email="viewer@marketing.test", password_hash=hash_password("Password123!"), full_name="Viewer User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_VIEWER))
    db_session.commit()
    return user


def _auth_headers(user, company, role):
    token = create_access_token(user_id=user.id, active_company_id=company.id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner_headers(owner_user, company):
    return _auth_headers(owner_user, company, ROLE_OWNER)


@pytest.fixture()
def viewer_headers(viewer_user, company):
    return _auth_headers(viewer_user, company, ROLE_VIEWER)


@pytest.fixture()
def campaign(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/marketing/campaigns",
        headers=owner_headers,
        json={"name": "Instagram Ramazan 2026", "channel": "instagram", "budget": "500.00"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
