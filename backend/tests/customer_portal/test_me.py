"""Customer-facing read endpoints. Every list/get here is hard-scoped to the
caller's own (company_id, customer_id) from their token -- these tests
exist specifically to prove that scoping, not just that the endpoints
return data."""
import io


def test_get_profile(app_client, portal_headers, customer, company):
    resp = app_client.get("/api/v1/customer_portal/me", headers=portal_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["customer_id"] == str(customer.id)
    assert body["name"] == customer.name
    assert body["company_id"] == str(company.id)
    assert body["company_name"] == company.name


def test_unauthenticated_me_request_401(app_client):
    resp = app_client.get("/api/v1/customer_portal/me")
    assert resp.status_code == 401


def test_list_and_get_own_order(app_client, portal_headers, ready_order):
    listed = app_client.get("/api/v1/customer_portal/me/orders", headers=portal_headers)
    assert listed.status_code == 200, listed.text
    ids = [o["id"] for o in listed.json()["items"]]
    assert ready_order["id"] in ids

    detail = app_client.get(f"/api/v1/customer_portal/me/orders/{ready_order['id']}", headers=portal_headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "ready"
    assert body["total_final"] == "442.50"
    # Internal cost/profit must never be exposed to the customer.
    assert "total_internal_cost" not in body
    assert "total_profit" not in body


def test_order_ownership_is_enforced(app_client, db_session, company, owner_headers, ready_order):
    from core.auth.security import create_access_token
    from modules.crm.infrastructure.models.customer import Customer

    other_customer = Customer(company_id=company.id, name="Other Customer", status="approved", type="individual")
    db_session.add(other_customer)
    db_session.commit()

    from modules.customer_portal.infrastructure.models.customer_login import CustomerLogin
    from core.auth.security import hash_password

    other_login = CustomerLogin(
        company_id=company.id,
        customer_id=other_customer.id,
        email="other@portal.test",
        password_hash=hash_password("Whatever123!"),
    )
    db_session.add(other_login)
    db_session.commit()

    other_token = app_client.post(
        "/api/v1/customer_portal/auth/login", json={"email": "other@portal.test", "password": "Whatever123!"}
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    resp = app_client.get(f"/api/v1/customer_portal/me/orders/{ready_order['id']}", headers=other_headers)
    assert resp.status_code == 404


def test_list_quotes_hides_drafts(app_client, portal_headers, accepted_quote, draft_quote):
    resp = app_client.get("/api/v1/customer_portal/me/quotes", headers=portal_headers)
    assert resp.status_code == 200, resp.text
    ids = [q["id"] for q in resp.json()["items"]]
    assert str(accepted_quote.id) in ids
    assert str(draft_quote.id) not in ids


def test_get_draft_quote_404(app_client, portal_headers, draft_quote):
    resp = app_client.get(f"/api/v1/customer_portal/me/quotes/{draft_quote.id}", headers=portal_headers)
    assert resp.status_code == 404


def test_get_accepted_quote_hides_internal_fields(app_client, portal_headers, accepted_quote):
    resp = app_client.get(f"/api/v1/customer_portal/me/quotes/{accepted_quote.id}", headers=portal_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["customer_notes"] == "Thanks for choosing us!"
    assert "internal_notes" not in body
    assert "total_internal_cost" not in body
    assert "profit_margin_pct" not in body


def _second_ready_order(app_client, db_session, owner_headers, company, customer):
    """A second Project -> accepted Quote -> ready Order for the same
    customer, mirroring tests/marketing/test_performance.py's own
    _create_ready_order_for_customer helper -- Invoice/InstallationJob are
    unique per order, so proving a *draft* invoice is hidden needs an order
    of its own, separate from the `ready_order`/`sent_invoice` fixtures."""
    from modules.sales.infrastructure.models.project import Project
    from modules.sales.infrastructure.models.quote import Quote
    from modules.sales.infrastructure.models.quote_section import QuoteSection
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    project = Project(company_id=company.id, customer_id=customer.id, name="Second Project", project_type="bathroom")
    db_session.add(project)
    db_session.flush()

    quote = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer.id,
        version=1,
        quote_number="QT-2026-0003-v1",
        status="accepted",
        currency="AZN",
        subtotal_gross="500.00",
        subtotal_after_discount="500.00",
        vat_amount="90.00",
        total_final="590.00",
        total_internal_cost="300.00",
        total_profit="200.00",
    )
    db_session.add(quote)
    db_session.flush()

    section = QuoteSection(company_id=company.id, quote_id=quote.id, name="Main Section", sort_order=0)
    db_session.add(section)
    db_session.flush()
    db_session.add(
        QuoteSectionItem(
            company_id=company.id,
            section_id=section.id,
            quote_id=quote.id,
            item_type="material",
            sort_order=0,
            description="Granite vanity top",
            quantity="1",
            unit="m2",
            unit_sale_price="500.00",
            unit_cost_price="300.00",
            line_total_sale="500.00",
            line_total_cost="300.00",
        )
    )
    db_session.commit()

    order = app_client.post("/api/v1/orders", headers=owner_headers, json={"quote_id": str(quote.id)}).json()
    for status in ("approved_for_production", "in_production", "ready"):
        resp = app_client.post(f"/api/v1/orders/{order['id']}/status", headers=owner_headers, json={"status": status})
        assert resp.status_code == 200, resp.text
    return resp.json()


def test_list_invoices_hides_drafts(app_client, db_session, portal_headers, owner_headers, company, customer, sent_invoice):
    second_order = _second_ready_order(app_client, db_session, owner_headers, company, customer)
    draft_invoice = app_client.post(
        "/api/v1/finance/invoices", headers=owner_headers, json={"order_id": second_order["id"]}
    ).json()

    resp = app_client.get("/api/v1/customer_portal/me/invoices", headers=portal_headers)
    assert resp.status_code == 200, resp.text
    ids = [i["id"] for i in resp.json()["items"]]
    assert sent_invoice["id"] in ids
    assert draft_invoice["id"] not in ids

    detail = app_client.get(f"/api/v1/customer_portal/me/invoices/{draft_invoice['id']}", headers=portal_headers)
    assert detail.status_code == 404


def test_get_invoice_detail_shows_balance_due(app_client, portal_headers, sent_invoice):
    resp = app_client.get(f"/api/v1/customer_portal/me/invoices/{sent_invoice['id']}", headers=portal_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sent"
    assert body["balance_due"] == body["total_amount"]


def test_list_and_get_installation_job(app_client, portal_headers, installation_job):
    listed = app_client.get("/api/v1/customer_portal/me/installation-jobs", headers=portal_headers)
    assert listed.status_code == 200, listed.text
    ids = [j["id"] for j in listed.json()["items"]]
    assert installation_job["id"] in ids

    detail = app_client.get(
        f"/api/v1/customer_portal/me/installation-jobs/{installation_job['id']}", headers=portal_headers
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "scheduled"


def test_documents_visible_and_hidden(app_client, owner_headers, portal_headers, customer, installation_job):
    customer_doc = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "crm", "related_entity_type": "customer", "related_entity_id": str(customer.id)},
        files={"file": ("contract.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert customer_doc.status_code == 200, customer_doc.text

    job_doc = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "installation", "related_entity_type": "installation_job", "related_entity_id": installation_job["id"]},
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )
    assert job_doc.status_code == 200, job_doc.text

    unrelated_doc = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "communication", "related_entity_type": "message", "related_entity_id": installation_job["id"]},
        files={"file": ("attachment.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert unrelated_doc.status_code == 200, unrelated_doc.text

    listed = app_client.get("/api/v1/customer_portal/me/documents", headers=portal_headers)
    assert listed.status_code == 200, listed.text
    ids = [d["id"] for d in listed.json()["items"]]
    assert customer_doc.json()["id"] in ids
    assert job_doc.json()["id"] in ids
    assert unrelated_doc.json()["id"] not in ids

    download = app_client.get(
        f"/api/v1/customer_portal/me/documents/{customer_doc.json()['id']}/download", headers=portal_headers
    )
    assert download.status_code == 200, download.text
    assert download.json()["url"]

    forbidden_download = app_client.get(
        f"/api/v1/customer_portal/me/documents/{unrelated_doc.json()['id']}/download", headers=portal_headers
    )
    assert forbidden_download.status_code == 404
