import pytest

from core.auth.models import ROLE_OWNER, ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.catalog.infrastructure.models.brand import Brand
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.crm.infrastructure.models.customer import Customer


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE GALLERY",
        slug="g-stone-gallery-sales",
        enabled_modules=["crm", "catalog", "sales"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(
        email="owner@sales.test",
        password_hash=hash_password("Password123!"),
        full_name="Owner User",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(
        email="viewer@sales.test",
        password_hash=hash_password("Password123!"),
        full_name="Viewer User",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_VIEWER))
    db_session.commit()
    return user


@pytest.fixture()
def customer(db_session, company):
    c = Customer(
        company_id=company.id,
        name="Test Customer",
        status="active",
        type="individual",
    )
    db_session.add(c)
    db_session.commit()
    return c


@pytest.fixture()
def material(db_session, company):
    brand = Brand(company_id=company.id, name="NEOLITH")
    db_session.add(brand)
    db_session.flush()
    m = StoneMaterial(
        company_id=company.id,
        brand_id=brand.id,
        name="Calacatta Gold",
        thickness_mm="12",
        dimensions="3200x1600mm",
    )
    db_session.add(m)
    db_session.commit()
    return m


def _auth_headers(user, company, role):
    token = create_access_token(user_id=user.id, active_company_id=company.id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner_headers(owner_user, company):
    return _auth_headers(owner_user, company, ROLE_OWNER)


@pytest.fixture()
def viewer_headers(viewer_user, company):
    return _auth_headers(viewer_user, company, ROLE_VIEWER)
