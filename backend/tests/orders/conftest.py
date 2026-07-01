import pytest

from core.auth.models import ROLE_OWNER, ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.crm.infrastructure.models.customer import Customer
from modules.sales.infrastructure.models.project import Project
from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem
from modules.sales.infrastructure.models.quote_section_measurement import QuoteSectionMeasurement


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE ORDERS TEST",
        slug="g-stone-orders-test",
        enabled_modules=["crm", "catalog", "sales", "orders"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(
        email="owner@orders.test",
        password_hash=hash_password("Password123!"),
        full_name="Owner User",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
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
def project(db_session, company, customer):
    p = Project(
        company_id=company.id,
        customer_id=customer.id,
        name="Kitchen Reno",
    )
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture()
def accepted_quote(db_session, company, project, customer):
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

    sec = QuoteSection(
        company_id=company.id,
        quote_id=q.id,
        name="Main Section",
        sort_order=0,
    )
    db_session.add(sec)
    db_session.flush()

    item = QuoteSectionItem(
        company_id=company.id,
        section_id=sec.id,
        quote_id=q.id,
        item_type="material",
        sort_order=0,
        description="Marble countertop",
        quantity="2.5",
        unit="m2",
        unit_sale_price="150.00",
        unit_cost_price="100.00",
        line_total_sale="375.00",
        line_total_cost="250.00",
    )
    db_session.add(item)

    meas = QuoteSectionMeasurement(
        company_id=company.id,
        section_id=sec.id,
        quote_id=q.id,
        sort_order=0,
        label="Island top",
        quantity=1,
        waste_pct="10",
    )
    db_session.add(meas)
    db_session.commit()
    return q


@pytest.fixture()
def draft_quote(db_session, company, project, customer):
    q = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer.id,
        version=1,
        quote_number="QT-2026-0002-v1",
        status="draft",
        currency="AZN",
    )
    db_session.add(q)
    db_session.commit()
    return q


def _auth_headers(user, company, role):
    token = create_access_token(user_id=user.id, active_company_id=company.id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner_headers(owner_user, company):
    return _auth_headers(owner_user, company, ROLE_OWNER)
