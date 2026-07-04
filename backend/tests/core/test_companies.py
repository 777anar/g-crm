"""Tests for the core companies endpoints."""
import pytest

from core.auth.models import ROLE_MANAGER, ROLE_OWNER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company


@pytest.fixture()
def company(db_session):
    company = Company(name="G-STONE CORE TEST", slug="g-stone-core-test", enabled_modules=["crm"])
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="owner@core.test", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


@pytest.fixture()
def manager_user(db_session, company):
    user = User(email="manager@core.test", password_hash=hash_password("Password123!"), full_name="Manager User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_MANAGER))
    db_session.commit()
    return user


@pytest.fixture()
def owner_headers(owner_user, company):
    token = create_access_token(user_id=owner_user.id, active_company_id=company.id, role=ROLE_OWNER)
    return {"Authorization": f"Bearer {token}"}


def test_list_company_users(app_client, owner_headers, owner_user, manager_user):
    resp = app_client.get("/api/v1/core/companies/users", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    emails = {u["email"] for u in resp.json()}
    assert emails == {"owner@core.test", "manager@core.test"}


def test_list_company_users_requires_auth(app_client):
    resp = app_client.get("/api/v1/core/companies/users")
    assert resp.status_code == 401
