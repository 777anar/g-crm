"""Tests for AI draft generation (Phase 21 follow-through): suggested Quote
line items from a Project's Rooms/Items via POST /ai/projects/{id}/draft-
quote-items -- draft-only, never creates a Quote or QuoteSectionItem."""
import pytest

from modules.catalog.infrastructure.models.price_list import PriceList, PriceListEntry
from modules.sales.infrastructure.models.project_item import ProjectItem
from modules.sales.infrastructure.models.room import Room


@pytest.fixture()
def room(db_session, company, project):
    r = Room(company_id=company.id, project_id=project.id, name="Kitchen")
    db_session.add(r)
    db_session.commit()
    return r


@pytest.fixture()
def project_item(db_session, company, project, room, material):
    item = ProjectItem(
        company_id=company.id, project_id=project.id, room_id=room.id,
        name="Countertop", material_id=material.id, quantity="5.000", unit="m2",
    )
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture()
def default_price_list_entry(db_session, company, material):
    price_list = PriceList(company_id=company.id, name="Retail", currency="AZN", is_default=True, status="active")
    db_session.add(price_list)
    db_session.flush()
    entry = PriceListEntry(
        company_id=company.id, price_list_id=price_list.id, material_id=material.id,
        cost_price="100.00", sale_price="150.00",
    )
    db_session.add(entry)
    db_session.commit()
    return entry


def test_draft_quote_items_creates_recommendation_with_estimated_totals(
    app_client, owner_headers, project, project_item, default_price_list_entry
):
    resp = app_client.post(
        f"/api/v1/ai/projects/{project.id}/draft-quote-items", headers=owner_headers, json={}
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    rec = items[0]
    assert rec["recommendation_type"] == "quote_draft_line_items"
    assert rec["analysis_kind"] == "quote"
    assert rec["related_entity_type"] == "project"
    assert rec["related_entity_id"] == str(project.id)

    drafted = rec["response"]["items"]
    assert len(drafted) == 1
    line = drafted[0]
    assert line["project_item_id"] == str(project_item.id)
    assert line["room_name"] == "Kitchen"
    assert line["material_name"] == "Calacatta Gold"
    assert line["unit_sale_price"] == "150.00"
    # m2-unit item -> mock's waste-factor heuristic applies 10%, so the
    # suggested quantity and estimated total both reflect the real math,
    # not anything the provider invented.
    assert float(line["suggested_quantity"]) == pytest.approx(5.5)
    assert float(line["estimated_total"]) == pytest.approx(5.5 * 150.0, rel=1e-3)


def test_draft_quote_items_without_default_price_list_has_no_price(app_client, owner_headers, project, project_item):
    resp = app_client.post(
        f"/api/v1/ai/projects/{project.id}/draft-quote-items", headers=owner_headers, json={}
    )
    assert resp.status_code == 200, resp.text
    line = resp.json()["items"][0]["response"]["items"][0]
    assert line["unit_sale_price"] is None
    assert line["estimated_total"] is None


def test_draft_quote_items_with_no_items_returns_empty_draft(app_client, owner_headers, project, room):
    resp = app_client.post(
        f"/api/v1/ai/projects/{project.id}/draft-quote-items", headers=owner_headers, json={}
    )
    assert resp.status_code == 200, resp.text
    rec = resp.json()["items"][0]
    assert rec["response"]["items"] == []


def test_draft_quote_items_never_creates_a_quote(app_client, owner_headers, project, project_item, db_session):
    from modules.sales.infrastructure.models.quote import Quote

    before = db_session.query(Quote).count()
    app_client.post(f"/api/v1/ai/projects/{project.id}/draft-quote-items", headers=owner_headers, json={})
    after = db_session.query(Quote).count()
    assert after == before


def test_draft_quote_items_unknown_project_returns_404(app_client, owner_headers):
    import uuid

    resp = app_client.post(f"/api/v1/ai/projects/{uuid.uuid4()}/draft-quote-items", headers=owner_headers, json={})
    assert resp.status_code == 404


def test_draft_quote_items_requires_write_permission(app_client, viewer_headers, project):
    resp = app_client.post(
        f"/api/v1/ai/projects/{project.id}/draft-quote-items", headers=viewer_headers, json={}
    )
    assert resp.status_code == 403
