"""Tests for Marketing's campaign performance/attribution -- the real
business value of the module: how many leads a campaign generated, how many
converted, and how much real revenue is attributable to it."""


def _create_ready_order_for_customer(app_client, db_session, owner_headers, company, customer_id, suffix):
    """Builds a Project -> accepted Quote -> Order (advanced to 'ready', a
    revenue-counted status) for an existing customer, mirroring the
    conftest patterns already established in tests/finance and
    tests/installation."""
    from modules.sales.infrastructure.models.project import Project
    from modules.sales.infrastructure.models.quote import Quote
    from modules.sales.infrastructure.models.quote_section import QuoteSection
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    project = Project(company_id=company.id, customer_id=customer_id, name=f"Project {suffix}", project_type="kitchen")
    db_session.add(project)
    db_session.flush()

    quote = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer_id,
        version=1,
        quote_number=f"QT-2026-{suffix}-v1",
        status="accepted",
        currency="AZN",
        subtotal_gross="1000.00",
        subtotal_after_discount="1000.00",
        vat_amount="180.00",
        total_final="1180.00",
        total_internal_cost="700.00",
        total_profit="480.00",
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
            description="Marble countertop",
            quantity="1",
            unit="m2",
            unit_sale_price="1000.00",
            unit_cost_price="700.00",
            line_total_sale="1000.00",
            line_total_cost="700.00",
        )
    )
    db_session.commit()

    order = app_client.post("/api/v1/orders", headers=owner_headers, json={"quote_id": str(quote.id)}).json()
    for status in ("approved_for_production", "in_production", "ready"):
        resp = app_client.post(f"/api/v1/orders/{order['id']}/status", headers=owner_headers, json={"status": status})
        assert resp.status_code == 200, resp.text
    return resp.json()


def test_performance_with_no_leads_returns_zeros(app_client, owner_headers, campaign):
    resp = app_client.get(f"/api/v1/marketing/campaigns/{campaign['id']}/performance", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["leads_count"] == 0
    assert body["converted_count"] == 0
    assert body["conversion_rate"] == 0
    assert body["attributed_revenue"] == "0"


def test_performance_counts_leads_and_conversion_rate(app_client, owner_headers, campaign):
    leads = []
    for i in range(4):
        resp = app_client.post(
            "/api/v1/crm/leads",
            headers=owner_headers,
            json={"full_name": f"Lead {i}", "source_channel": "instagram", "campaign_id": campaign["id"]},
        )
        assert resp.status_code == 200, resp.text
        leads.append(resp.json())

    # Convert 2 of the 4 leads captured under this campaign.
    for lead in leads[:2]:
        convert = app_client.post(f"/api/v1/crm/leads/{lead['id']}/convert", headers=owner_headers)
        assert convert.status_code == 200, convert.text

    # A lead captured with no campaign_id must not be counted.
    app_client.post(
        "/api/v1/crm/leads", headers=owner_headers, json={"full_name": "Unrelated Lead", "source_channel": "website"}
    )

    resp = app_client.get(f"/api/v1/marketing/campaigns/{campaign['id']}/performance", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["leads_count"] == 4
    assert body["converted_count"] == 2
    assert body["conversion_rate"] == 0.5


def test_performance_attributes_revenue_from_converted_customer_orders(
    app_client, db_session, owner_headers, company, campaign
):
    lead = app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={"full_name": "Rovshan Aliyev", "source_channel": "instagram", "campaign_id": campaign["id"]},
    ).json()
    converted = app_client.post(f"/api/v1/crm/leads/{lead['id']}/convert", headers=owner_headers).json()
    customer_id = converted["customer_id"]

    order = _create_ready_order_for_customer(app_client, db_session, owner_headers, company, customer_id, "REV1")
    assert order["status"] == "ready"

    resp = app_client.get(f"/api/v1/marketing/campaigns/{campaign['id']}/performance", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["leads_count"] == 1
    assert body["converted_count"] == 1
    assert body["attributed_revenue"] == "1180.00"


def test_performance_ignores_cancelled_orders(app_client, db_session, owner_headers, company, campaign):
    lead = app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={"full_name": "Aysel Mammadova", "source_channel": "instagram", "campaign_id": campaign["id"]},
    ).json()
    converted = app_client.post(f"/api/v1/crm/leads/{lead['id']}/convert", headers=owner_headers).json()
    customer_id = converted["customer_id"]

    order = _create_ready_order_for_customer(app_client, db_session, owner_headers, company, customer_id, "REV2")
    cancel_resp = app_client.post(
        f"/api/v1/orders/{order['id']}/status", headers=owner_headers, json={"status": "cancelled"}
    )
    assert cancel_resp.status_code == 200, cancel_resp.text

    resp = app_client.get(f"/api/v1/marketing/campaigns/{campaign['id']}/performance", headers=owner_headers)
    body = resp.json()
    assert body["attributed_revenue"] == "0"
