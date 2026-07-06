import pytest

from core.auth.models import ROLE_OWNER, ROLE_REP, ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.catalog.infrastructure.models.brand import Brand
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.communication.infrastructure.models.channel import Channel
from modules.communication.infrastructure.models.conversation import Conversation
from modules.communication.infrastructure.models.message import Message
from modules.crm.infrastructure.models.customer import Customer
from modules.crm.infrastructure.models.lead import Lead
from modules.sales.infrastructure.models.project import Project
from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE AI TEST",
        slug="g-stone-ai-test",
        enabled_modules=["crm", "catalog", "sales", "orders", "communication", "ai"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="owner@ai.test", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(email="viewer@ai.test", password_hash=hash_password("Password123!"), full_name="Viewer User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_VIEWER))
    db_session.commit()
    return user


@pytest.fixture()
def rep_user(db_session, company):
    user = User(email="rep@ai.test", password_hash=hash_password("Password123!"), full_name="Rep User")
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
def lead(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={
            "full_name": "Rashad Aliyev",
            "source_channel": "whatsapp",
            "email": "rashad@example.com",
            "phone": "+994501234567",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def bare_lead(app_client, owner_headers):
    """A lead with no email/phone -- for missing-info detection."""
    resp = app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={"full_name": "Anonymous Contact", "source_channel": "other"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def customer(db_session, company):
    c = Customer(
        company_id=company.id,
        name="Existing Customer",
        status="approved",
        type="individual",
        email="existing@example.com",
        phone="+994507654321",
    )
    db_session.add(c)
    db_session.commit()
    return c


@pytest.fixture()
def brand(db_session, company):
    b = Brand(company_id=company.id, name="NEOLITH", status="active")
    db_session.add(b)
    db_session.commit()
    return b


@pytest.fixture()
def material(db_session, company, brand):
    m = StoneMaterial(company_id=company.id, brand_id=brand.id, name="Calacatta Gold", material_type="Sintered Stone", status="active")
    db_session.add(m)
    db_session.commit()
    return m


@pytest.fixture()
def premium_material(db_session, company, brand):
    """Same material_type as `material`, priced higher in history -- the
    upsell candidate."""
    m = StoneMaterial(company_id=company.id, brand_id=brand.id, name="Calacatta Premium", material_type="Sintered Stone", status="active")
    db_session.add(m)
    db_session.commit()
    return m


@pytest.fixture()
def complementary_material(db_session, company, brand):
    m = StoneMaterial(company_id=company.id, brand_id=brand.id, name="Edge Profile Trim", material_type="Accessory", status="active")
    db_session.add(m)
    db_session.commit()
    return m


@pytest.fixture()
def project(db_session, company, customer):
    p = Project(company_id=company.id, customer_id=customer.id, name="Kitchen Reno", project_type="kitchen")
    db_session.add(p)
    db_session.commit()
    return p


def _make_accepted_quote(db_session, company, project, customer, *, quote_number, material, other_material, unit_sale_price):
    q = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer.id,
        version=1,
        quote_number=quote_number,
        status="accepted",
        currency="AZN",
        subtotal_gross="1000.00",
        discount_amount="50.00",
        subtotal_after_discount="950.00",
        vat_amount="171.00",
        total_final="1121.00",
        total_internal_cost="600.00",
        total_profit="350.00",
    )
    db_session.add(q)
    db_session.flush()

    section = QuoteSection(company_id=company.id, quote_id=q.id, name="Main Section", sort_order=0)
    db_session.add(section)
    db_session.flush()

    db_session.add(QuoteSectionItem(
        company_id=company.id, section_id=section.id, quote_id=q.id, item_type="material", sort_order=0,
        description=f"{material.name} countertop", material_id=material.id, quantity="2.5", unit="m2",
        unit_sale_price=unit_sale_price, unit_cost_price="100.00",
        line_total_sale=str(float(unit_sale_price) * 2.5), line_total_cost="250.00",
    ))
    if other_material:
        db_session.add(QuoteSectionItem(
            company_id=company.id, section_id=section.id, quote_id=q.id, item_type="material", sort_order=1,
            description=f"{other_material.name} accessory", material_id=other_material.id, quantity="1", unit="unit",
            unit_sale_price="80.00", unit_cost_price="40.00", line_total_sale="80.00", line_total_cost="40.00",
        ))
    db_session.commit()
    return q


@pytest.fixture()
def historical_accepted_quotes(db_session, company, project, customer, material, premium_material, complementary_material):
    """A handful of this company's own past accepted quotes -- the
    transaction history AnalyzeQuoteUseCase learns product/cross-sell/
    upsell/discount/pricing signal from."""
    quotes = [
        _make_accepted_quote(
            db_session, company, project, customer, quote_number=f"QT-HIST-{i}",
            material=material if i % 2 == 0 else premium_material,
            other_material=complementary_material, unit_sale_price="150.00" if i % 2 == 0 else "220.00",
        )
        for i in range(4)
    ]
    return quotes


@pytest.fixture()
def draft_quote(db_session, company, project, customer, material):
    q = Quote(
        company_id=company.id, project_id=project.id, customer_id=customer.id, version=1,
        quote_number="QT-DRAFT-1", status="draft", currency="AZN",
        subtotal_gross="375.00", subtotal_after_discount="375.00", vat_amount="67.50", total_final="442.50",
        total_internal_cost="250.00", total_profit="192.50",
    )
    db_session.add(q)
    db_session.flush()
    section = QuoteSection(company_id=company.id, quote_id=q.id, name="Main Section", sort_order=0, total_measured_area="12.5")
    db_session.add(section)
    db_session.flush()
    db_session.add(QuoteSectionItem(
        company_id=company.id, section_id=section.id, quote_id=q.id, item_type="material", sort_order=0,
        description=f"{material.name} countertop", material_id=material.id, quantity="2.5", unit="m2",
        unit_sale_price="150.00", unit_cost_price="140.00", line_total_sale="375.00", line_total_cost="350.00",
    ))
    db_session.commit()
    return q


@pytest.fixture()
def channel(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "whatsapp", "display_name": "Sales WhatsApp", "identifier": "+994501111111"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def conversation(db_session, company, channel):
    conv = Conversation(
        company_id=company.id, channel_id=channel["id"], external_contact_id="+994509998877",
        external_contact_name="Test Contact", status="open", unread_count=1,
    )
    db_session.add(conv)
    db_session.flush()
    db_session.add(Message(
        company_id=company.id, conversation_id=conv.id, direction="inbound", sender_type="customer",
        message_type="text", body="Hi, this is urgent! What is the price for Calacatta Gold? My email is buyer@example.com",
        status="received",
    ))
    db_session.commit()
    db_session.refresh(conv)
    return conv
