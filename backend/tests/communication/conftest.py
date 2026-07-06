import pytest

from core.auth.models import ROLE_OWNER, ROLE_REP, ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.crm.infrastructure.models.customer import Customer


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE COMMUNICATION TEST",
        slug="g-stone-communication-test",
        enabled_modules=["crm", "sales", "orders", "communication"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="owner@comm.test", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(email="viewer@comm.test", password_hash=hash_password("Password123!"), full_name="Viewer User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_VIEWER))
    db_session.commit()
    return user


@pytest.fixture()
def rep_user(db_session, company):
    user = User(email="rep@comm.test", password_hash=hash_password("Password123!"), full_name="Rep User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_REP))
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
def rep_headers(rep_user, company):
    return _auth_headers(rep_user, company, ROLE_REP)


@pytest.fixture()
def known_customer(db_session, company):
    customer = Customer(
        company_id=company.id,
        name="Rashad Aliyev",
        status="approved",
        type="individual",
        whatsapp="+994501234567",
        email="rashad@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture()
def whatsapp_channel(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "whatsapp", "display_name": "Sales WhatsApp", "identifier": "+994501111111"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
