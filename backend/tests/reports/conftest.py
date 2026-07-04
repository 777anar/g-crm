import pytest

from core.auth.models import ROLE_OWNER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.crm.infrastructure.models.customer import Customer
from modules.crm.infrastructure.models.lead import Lead
from modules.sales.infrastructure.models.project import Project
from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE REPORTS TEST",
        slug="g-stone-reports-test",
        enabled_modules=["crm", "catalog", "sales", "orders", "installation", "reports"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(
        email="owner@reports.test",
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
def lost_customer(db_session, company):
    c = Customer(company_id=company.id, name="Lost Customer", status="lost", type="individual")
    db_session.add(c)
    db_session.commit()
    return c


@pytest.fixture()
def lead(db_session, company):
    lead = Lead(company_id=company.id, full_name="Jane Lead", source_channel="instagram", status="new")
    db_session.add(lead)
    db_session.commit()
    return lead


@pytest.fixture()
def project(db_session, company, customer):
    p = Project(company_id=company.id, customer_id=customer.id, name="Kitchen Reno", project_type="kitchen")
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
        subtotal_gross="375.00",
        subtotal_after_discount="375.00",
        vat_amount="67.50",
        total_final="442.50",
        total_internal_cost="250.00",
        total_profit="192.50",
    )
    db_session.add(q)
    db_session.flush()

    sec = QuoteSection(company_id=company.id, quote_id=q.id, name="Main Section", sort_order=0)
    db_session.add(sec)
    db_session.flush()

    db_session.add(QuoteSectionItem(
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
    ))
    db_session.commit()
    return q


@pytest.fixture()
def order(app_client, owner_headers, accepted_quote):
    """An order created (and its section/items copied) via the real Orders
    API -- so its financial snapshot and audit trail are exactly what
    production traffic would produce."""
    resp = app_client.post(
        "/api/v1/orders",
        headers=owner_headers,
        json={"quote_id": str(accepted_quote.id)},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def order_in_production(app_client, owner_headers, order):
    for status in ("approved_for_production", "in_production"):
        resp = app_client.post(
            f"/api/v1/orders/{order['id']}/status",
            headers=owner_headers,
            json={"status": status},
        )
        assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def completed_order(app_client, owner_headers, order_in_production):
    order_id = order_in_production["id"]
    for status in ("ready", "delivered", "installed", "completed"):
        resp = app_client.post(
            f"/api/v1/orders/{order_id}/status",
            headers=owner_headers,
            json={"status": status},
        )
        assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def ready_order(app_client, owner_headers, order_in_production):
    resp = app_client.post(
        f"/api/v1/orders/{order_in_production['id']}/status",
        headers=owner_headers,
        json={"status": "ready"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def completed_installation_job(app_client, owner_headers, owner_user, ready_order):
    """A real InstallationJob, assigned to a crew and driven to completion
    through the Installation module's own API -- so it advances the Order to
    'installed' itself (and populates crew productivity data) exactly like
    production traffic would."""
    crew = app_client.post(
        "/api/v1/installation/crews", headers=owner_headers, json={"name": "Test Crew"}
    ).json()
    app_client.post(
        f"/api/v1/installation/crews/{crew['id']}/members",
        headers=owner_headers,
        json={"user_id": str(owner_user.id), "is_lead": True},
    )

    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()
    app_client.patch(
        f"/api/v1/installation/jobs/{job['id']}", headers=owner_headers, json={"crew_id": crew["id"]}
    )
    for status in ("en_route", "in_progress", "completed"):
        resp = app_client.post(
            f"/api/v1/installation/jobs/{job['id']}/status",
            headers=owner_headers,
            json={"status": status},
        )
        assert resp.status_code == 200, resp.text
    return resp.json()
