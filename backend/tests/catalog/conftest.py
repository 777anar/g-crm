import pytest

from core.auth.models import ROLE_OWNER, ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company


@pytest.fixture()
def company(db_session):
    company = Company(name="G-STONE GALLERY", slug="g-stone-gallery-catalog", enabled_modules=["crm", "catalog"])
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="owner@catalog.test", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(email="viewer@catalog.test", password_hash=hash_password("Password123!"), full_name="Viewer User")
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
