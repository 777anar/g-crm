import pytest

from core.auth.models import ROLE_OWNER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.catalog.infrastructure.models.brand import Brand
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.catalog.infrastructure.models.slab import Slab
from modules.catalog.infrastructure.models.warehouse import Warehouse
from modules.crm.infrastructure.models.customer import Customer
from modules.sales.infrastructure.models.project import Project
from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE PRODUCTION TEST",
        slug="g-stone-production-test",
        enabled_modules=["crm", "catalog", "sales", "orders", "production"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(
        email="owner@production.test",
        password_hash=hash_password("Password123!"),
        full_name="Owner User",
    )
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
def customer(db_session, company):
    c = Customer(company_id=company.id, name="Test Customer", status="approved", type="individual")
    db_session.add(c)
    db_session.commit()
    return c


@pytest.fixture()
def project(db_session, company, customer):
    p = Project(company_id=company.id, customer_id=customer.id, name="Kitchen Reno", project_type="kitchen")
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture()
def slab(db_session, company):
    brand = Brand(company_id=company.id, name="NEOLITH")
    db_session.add(brand)
    db_session.flush()

    material = StoneMaterial(company_id=company.id, brand_id=brand.id, name="Calacatta Gold")
    db_session.add(material)
    db_session.flush()

    warehouse = Warehouse(company_id=company.id, name="Main Warehouse")
    db_session.add(warehouse)
    db_session.flush()

    s = Slab(
        company_id=company.id,
        material_id=material.id,
        warehouse_id=warehouse.id,
        slab_number="SLB-0001",
        length_mm="3200",
        width_mm="1600",
        area_m2="5.12",
        status="available",
    )
    db_session.add(s)
    db_session.commit()
    return s


@pytest.fixture()
def accepted_quote_with_slab(db_session, company, project, customer, slab):
    """An accepted quote whose single item is linked to `slab` -- accepting
    it reserves the slab, per modules/sales/application/use_cases/quote_use_cases.py."""
    q = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer.id,
        version=1,
        quote_number="QT-2026-0001-v1",
        status="accepted",
        currency="AZN",
    )
    db_session.add(q)
    db_session.flush()

    sec = QuoteSection(company_id=company.id, quote_id=q.id, name="Main Section", sort_order=0)
    db_session.add(sec)
    db_session.flush()

    item = QuoteSectionItem(
        company_id=company.id,
        section_id=sec.id,
        quote_id=q.id,
        item_type="material",
        sort_order=0,
        description="Marble countertop",
        slab_id=slab.id,
        quantity="2.5",
        unit="m2",
        unit_sale_price="150.00",
        unit_cost_price="100.00",
        line_total_sale="375.00",
        line_total_cost="250.00",
    )
    db_session.add(item)
    slab.status = "reserved"
    db_session.commit()
    return q


@pytest.fixture()
def approved_order(app_client, owner_headers, accepted_quote_with_slab):
    """An order, already advanced to approved_for_production -- the gate
    CreateWorkOrderUseCase requires."""
    order = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote_with_slab.id)},
    ).json()
    resp = app_client.post(
        f"/api/v1/orders/{order['id']}/status",
        headers=owner_headers,
        json={"status": "approved_for_production"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
