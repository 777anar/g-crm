import pytest

from core.auth.models import ROLE_OWNER, ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.catalog.infrastructure.models.brand import Brand
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.catalog.infrastructure.models.warehouse import Warehouse


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE PURCHASING TEST",
        slug="g-stone-purchasing-test",
        enabled_modules=["catalog", "purchasing"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="owner@purchasing.test", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(email="viewer@purchasing.test", password_hash=hash_password("Password123!"), full_name="Viewer User")
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
def material(db_session, company):
    brand = Brand(company_id=company.id, name="NEOLITH")
    db_session.add(brand)
    db_session.flush()
    m = StoneMaterial(company_id=company.id, brand_id=brand.id, name="Calacatta Gold")
    db_session.add(m)
    db_session.commit()
    return m


@pytest.fixture()
def warehouse(db_session, company):
    w = Warehouse(company_id=company.id, name="Main Warehouse")
    db_session.add(w)
    db_session.commit()
    return w


@pytest.fixture()
def supplier(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/purchasing/suppliers",
        headers=owner_headers,
        json={"name": "Marmi Carrara Srl", "contact_name": "Luca Bianchi", "email": "luca@marmicarrara.it"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def confirmed_po(app_client, owner_headers, supplier, material):
    """A purchase order with one material-linked line, already advanced to
    'confirmed' -- the earliest status a line can be received against."""
    po = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={
            "supplier_id": supplier["id"],
            "lines": [
                {
                    "material_id": str(material.id),
                    "description": "Calacatta Gold slabs, 20mm",
                    "quantity": "10",
                    "unit": "slab",
                    "unit_cost": "250.00",
                }
            ],
        },
    ).json()
    for status in ("pending_approval", "approved", "sent", "confirmed"):
        resp = app_client.post(
            f"/api/v1/purchasing/purchase-orders/{po['id']}/status", headers=owner_headers, json={"status": status}
        )
        assert resp.status_code == 200, resp.text
    return resp.json()
