"""Tests for Sales Intelligence: the AI Quote Assistant / AnalyzeQuoteUseCase."""


def _types(items):
    return [r["recommendation_type"] for r in items]


def test_analyze_quote_returns_discount_and_delivery_complexity(app_client, owner_headers, draft_quote):
    resp = app_client.post(f"/api/v1/ai/quotes/{draft_quote.id}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 200, resp.text
    types = _types(resp.json()["items"])
    assert "discount_recommendation" in types
    assert "delivery_complexity_estimate" in types


def test_delivery_complexity_is_valid_value(app_client, owner_headers, draft_quote):
    items = app_client.post(f"/api/v1/ai/quotes/{draft_quote.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "delivery_complexity_estimate")
    assert rec["response"]["complexity"] in ("low", "medium", "high")


def test_product_and_cross_sell_recommendations_from_history(app_client, owner_headers, draft_quote, historical_accepted_quotes, complementary_material):
    items = app_client.post(f"/api/v1/ai/quotes/{draft_quote.id}/analyze", headers=owner_headers, json={}).json()["items"]
    types = _types(items)
    assert "product_recommendation" in types
    assert "cross_sell_suggestion" in types
    cross_sell = next(r for r in items if r["recommendation_type"] == "cross_sell_suggestion")
    recommended_ids = [p["material_id"] for p in cross_sell["response"]["products"]]
    assert str(complementary_material.id) in recommended_ids


def test_upsell_suggestion_for_higher_priced_same_type_material(app_client, owner_headers, draft_quote, historical_accepted_quotes, premium_material):
    items = app_client.post(f"/api/v1/ai/quotes/{draft_quote.id}/analyze", headers=owner_headers, json={}).json()["items"]
    upsell = next((r for r in items if r["recommendation_type"] == "upsell_suggestion"), None)
    assert upsell is not None, "expected an upsell_suggestion recommendation"
    recommended_ids = [p["material_id"] for p in upsell["response"]["products"]]
    assert str(premium_material.id) in recommended_ids


def test_discount_recommendation_reflects_historical_average(app_client, owner_headers, draft_quote, historical_accepted_quotes):
    items = app_client.post(f"/api/v1/ai/quotes/{draft_quote.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "discount_recommendation")
    # historical_accepted_quotes fixture always discounts 50 off a 1000 subtotal_gross -> 5%
    assert rec["response"]["suggested_pct"] == 5.0


def test_margin_risk_detected_for_thin_margin_item(app_client, owner_headers, db_session, company, project, customer, material):
    from modules.sales.infrastructure.models.quote import Quote
    from modules.sales.infrastructure.models.quote_section import QuoteSection
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    quote = Quote(
        company_id=company.id, project_id=project.id, customer_id=customer.id, version=1,
        quote_number="QT-THIN-MARGIN", status="draft", currency="AZN",
        subtotal_gross="100.00", subtotal_after_discount="100.00", vat_amount="18.00", total_final="118.00",
        total_internal_cost="90.00", total_profit="10.00",
    )
    db_session.add(quote)
    db_session.flush()
    section = QuoteSection(company_id=company.id, quote_id=quote.id, name="Main", sort_order=0)
    db_session.add(section)
    db_session.flush()
    db_session.add(QuoteSectionItem(
        company_id=company.id, section_id=section.id, quote_id=quote.id, item_type="material", sort_order=0,
        description="Thin margin item", material_id=material.id, quantity="1", unit="unit",
        unit_sale_price="100.00", unit_cost_price="92.00", line_total_sale="100.00", line_total_cost="92.00",
    ))
    db_session.commit()

    items = app_client.post(f"/api/v1/ai/quotes/{quote.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "margin_risk_detection")
    assert len(rec["response"]["risks"]) == 1
    assert rec["response"]["risks"][0]["margin_pct"] == 8.0


def test_price_anomaly_detected_for_high_priced_item(app_client, owner_headers, draft_quote, historical_accepted_quotes, db_session, company, material):
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    item = db_session.query(QuoteSectionItem).filter(QuoteSectionItem.quote_id == draft_quote.id).first()
    item.unit_sale_price = "500.00"  # historical avg for `material` is 150.00
    db_session.commit()

    items = app_client.post(f"/api/v1/ai/quotes/{draft_quote.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "price_anomaly_detection")
    assert rec["response"]["anomalies"][0]["direction"] == "high"


def test_analyze_unknown_quote_returns_404(app_client, owner_headers):
    import uuid

    resp = app_client.post(f"/api/v1/ai/quotes/{uuid.uuid4()}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 404


def test_analyze_quote_requires_write_permission(app_client, viewer_headers, draft_quote):
    resp = app_client.post(f"/api/v1/ai/quotes/{draft_quote.id}/analyze", headers=viewer_headers, json={})
    assert resp.status_code == 403


def test_analyze_quote_writes_audit_and_event(app_client, owner_headers, db_session, company, draft_quote):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(f"/api/v1/ai/quotes/{draft_quote.id}/analyze", headers=owner_headers, json={})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "ai.quote_analyzed").first()
    assert entry is not None
    assert entry.company_id == company.id

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "QuoteAnalyzed" in events
