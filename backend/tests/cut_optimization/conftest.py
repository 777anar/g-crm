import pytest

from core.auth.models import ROLE_OWNER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.catalog.infrastructure.models.brand import Brand
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.catalog.infrastructure.models.warehouse import Warehouse


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE CUT-OPT TEST",
        slug="g-stone-cut-opt-test",
        enabled_modules=["catalog", "cut_optimization"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="owner@cutopt.test", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


def _auth_headers(user, company, role):
    token = create_access_token(user_id=user.id, active_company_id=company.id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner_headers(owner_user, company):
    return _auth_headers(owner_user, company, ROLE_OWNER)


@pytest.fixture()
def warehouse(db_session, company):
    w = Warehouse(company_id=company.id, name="Main Warehouse")
    db_session.add(w)
    db_session.commit()
    return w


@pytest.fixture()
def material(db_session, company):
    brand = Brand(company_id=company.id, name="NEOLITH")
    db_session.add(brand)
    db_session.flush()
    m = StoneMaterial(company_id=company.id, brand_id=brand.id, name="Calacatta Gold", finish="Polished", thickness_mm="20")
    db_session.add(m)
    db_session.commit()
    return m
