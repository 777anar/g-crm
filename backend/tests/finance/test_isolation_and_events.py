"""Multi-company isolation and audit/event verification for the Finance
module -- per the requirement that "everything must be multi-company", and
per the established pattern of recording an audit entry + domain event for
every write action."""


def test_invoices_are_isolated_by_company(app_client, db_session, owner_headers, ready_order, company):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-finance-test", enabled_modules=["finance"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@finance.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = app_client.get(f"/api/v1/finance/invoices/{invoice['id']}", headers=other_headers)
    assert response.status_code == 404

    other_company_invoices = app_client.get("/api/v1/finance/invoices", headers=other_headers).json()
    assert invoice["id"] not in [i["id"] for i in other_company_invoices["items"]]


def test_invoice_numbers_can_repeat_across_companies(app_client, db_session, owner_headers, ready_order):
    """The invoice-number sequence is scoped per company -- two different
    companies both raising their first invoice of the year both get
    'INV-<year>-0001' without conflict."""
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company
    from modules.crm.infrastructure.models.customer import Customer
    from modules.sales.infrastructure.models.project import Project
    from modules.sales.infrastructure.models.quote import Quote
    from modules.sales.infrastructure.models.quote_section import QuoteSection
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    first = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()
    assert first["invoice_number"].endswith("-0001")

    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-finance-seq-test", enabled_modules=["finance"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner-2@finance.test", password_hash=hash_password("x"), full_name="Other Owner 2")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))

    other_customer = Customer(company_id=other_company.id, name="Other Customer", status="approved", type="individual")
    db_session.add(other_customer)
    db_session.flush()
    other_project = Project(company_id=other_company.id, customer_id=other_customer.id, name="Other Reno", project_type="kitchen")
    db_session.add(other_project)
    db_session.flush()
    other_quote = Quote(
        company_id=other_company.id,
        project_id=other_project.id,
        customer_id=other_customer.id,
        version=1,
        quote_number="QT-2026-0001-v1",
        status="accepted",
        currency="AZN",
        subtotal_gross="100.00",
        subtotal_after_discount="100.00",
        vat_amount="18.00",
        total_final="118.00",
        total_internal_cost="60.00",
        total_profit="40.00",
    )
    db_session.add(other_quote)
    db_session.flush()
    other_section = QuoteSection(company_id=other_company.id, quote_id=other_quote.id, name="Main Section", sort_order=0)
    db_session.add(other_section)
    db_session.flush()
    db_session.add(QuoteSectionItem(
        company_id=other_company.id,
        section_id=other_section.id,
        quote_id=other_quote.id,
        item_type="material",
        sort_order=0,
        description="Granite countertop",
        quantity="1",
        unit="m2",
        unit_sale_price="100.00",
        unit_cost_price="60.00",
        line_total_sale="100.00",
        line_total_cost="60.00",
    ))
    db_session.commit()

    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    other_order = app_client.post(
        "/api/v1/orders", headers=other_headers, json={"quote_id": str(other_quote.id)}
    ).json()
    for status in ("approved_for_production", "in_production", "ready"):
        assert app_client.post(
            f"/api/v1/orders/{other_order['id']}/status", headers=other_headers, json={"status": status}
        ).status_code == 200

    other_invoice = app_client.post(
        "/api/v1/finance/invoices", headers=other_headers, json={"order_id": other_order["id"]}
    ).json()
    assert other_invoice["invoice_number"].endswith("-0001")
    assert other_invoice["invoice_number"] == first["invoice_number"]


def test_invoice_creation_writes_audit_and_event(app_client, owner_headers, db_session, owner_user, company, ready_order):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post("/api/v1/finance/invoices", headers=owner_headers, json={"order_id": ready_order["id"]})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "invoice.created").first()
    assert entry is not None
    assert entry.actor_user_id == owner_user.id
    assert entry.company_id == company.id
    assert entry.module == "finance"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "InvoiceCreated" in events


def test_payment_writes_audit_and_publishes_payment_received(app_client, owner_headers, db_session, sent_invoice):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(
        f"/api/v1/finance/invoices/{sent_invoice['id']}/payments",
        headers=owner_headers,
        json={"amount": "442.50", "method": "cash"},
    )

    actions = [r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == "invoice_payment").all()]
    assert "payment.recorded" in actions

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "PaymentReceived" in events
    assert "InvoiceStatusChanged" in events


def test_expense_creation_writes_audit_and_event(app_client, owner_headers, db_session, owner_user, company):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(
        "/api/v1/finance/expenses",
        headers=owner_headers,
        json={"category": "rent", "amount": "500.00", "expense_date": "2026-07-01"},
    )

    entry = db_session.query(AuditLog).filter(AuditLog.action == "expense.created").first()
    assert entry is not None
    assert entry.company_id == company.id
    assert entry.module == "finance"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "ExpenseCreated" in events
