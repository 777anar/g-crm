"""Stone-industry CRM customization (Phase 3 / G-STONE GALLERY): new
customer fields, sales-pipeline status, and the expanded lead source list."""
import pytest


def test_create_customer_with_full_stone_industry_fields(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={
            "name": "Elvin Mammadov",
            "type": "individual",
            "phone": "+994501112233",
            "whatsapp": "+994501112233",
            "instagram": "@elvin.stone",
            "facebook": "elvin.mammadov",
            "email": "elvin@example.com",
            "address": "28 May St, Baku",
            "company_name": "Mammadov Construction",
            "notes": "Wants a marble countertop, kitchen renovation.",
            "lead_source": "instagram",
            "advertising_campaign": "Summer Slab Sale",
            "status": "new_inquiry",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["phone"] == "+994501112233"
    assert body["whatsapp"] == "+994501112233"
    assert body["instagram"] == "@elvin.stone"
    assert body["facebook"] == "elvin.mammadov"
    assert body["email"] == "elvin@example.com"
    assert body["address"] == "28 May St, Baku"
    assert body["company_name"] == "Mammadov Construction"
    assert body["notes"] == "Wants a marble countertop, kitchen renovation."
    assert body["status"] == "new_inquiry"


def test_create_customer_defaults_to_new_inquiry_status(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Default Status Co", "type": "business"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "new_inquiry"


def test_create_customer_rejects_invalid_status(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Bad Status Co", "type": "business", "status": "in_orbit"},
    )
    assert response.status_code in (400, 422)


@pytest.mark.parametrize(
    "status",
    [
        "new_inquiry",
        "contacted",
        "measurement_scheduled",
        "measurement_completed",
        "preparing_quote",
        "quote_sent",
        "waiting_for_decision",
        "approved",
        "payment_received",
        "in_production",
        "installation_scheduled",
        "installed",
        "completed",
        "lost",
    ],
)
def test_update_customer_through_every_pipeline_status(app_client, owner_headers, status):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Pipeline Co", "type": "business"}
    ).json()

    response = app_client.patch(
        f"/api/v1/crm/customers/{created['id']}", headers=owner_headers, json={"status": status}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == status


def test_update_customer_rejects_invalid_status(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Invalid Status Co", "type": "business"}
    ).json()
    response = app_client.patch(
        f"/api/v1/crm/customers/{created['id']}", headers=owner_headers, json={"status": "teleported"}
    )
    assert response.status_code in (400, 422)


def test_status_change_writes_audit_and_event(app_client, owner_headers, db_session):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Status Event Co", "type": "business"}
    ).json()
    app_client.patch(f"/api/v1/crm/customers/{created['id']}", headers=owner_headers, json={"status": "contacted"})

    actions = [r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == "customer").all()]
    assert "customer.updated" in actions

    events = [r.event_name for r in db_session.query(EventLogEntry).all()]
    assert "CustomerStatusChanged" in events


@pytest.mark.parametrize(
    "channel",
    ["instagram", "facebook", "messenger", "whatsapp", "phone_call", "website", "office_visit", "referral", "other"],
)
def test_customer_lead_source_accepts_every_stone_industry_channel(app_client, owner_headers, channel):
    response = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": f"Lead Source {channel}", "type": "individual", "lead_source": channel},
    )
    assert response.status_code == 200, response.text
    assert response.json()["lead_source"] == channel


def test_customer_lead_source_rejects_old_manual_value(app_client, owner_headers):
    """'manual' was replaced by office_visit/phone_call/referral/other in the
    stone-industry lead source list -- it must no longer validate."""
    response = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Old Manual Co", "type": "individual", "lead_source": "manual"},
    )
    assert response.status_code in (400, 422)


def test_list_customers_filter_by_status(app_client, owner_headers):
    c1 = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "In Production Co", "type": "business"}
    ).json()
    app_client.patch(f"/api/v1/crm/customers/{c1['id']}", headers=owner_headers, json={"status": "in_production"})
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Still New Co", "type": "business"})

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"status": "in_production"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(c["status"] == "in_production" for c in items)
    assert any(c["name"] == "In Production Co" for c in items)
    assert not any(c["name"] == "Still New Co" for c in items)


def test_list_customers_filter_by_lead_source(app_client, owner_headers):
    app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Referral Co", "type": "business", "lead_source": "referral"},
    )
    app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={"name": "Website Co", "type": "business", "lead_source": "website"},
    )

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"lead_source": "referral"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(c["lead_source"] == "referral" for c in items)
    assert any(c["name"] == "Referral Co" for c in items)
    assert not any(c["name"] == "Website Co" for c in items)


@pytest.mark.parametrize(
    "channel",
    ["instagram", "facebook", "messenger", "whatsapp", "phone_call", "website", "office_visit", "referral", "other"],
)
def test_lead_creation_accepts_every_stone_industry_channel(app_client, owner_headers, channel):
    response = app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={"full_name": f"Lead via {channel}", "source_channel": channel},
    )
    assert response.status_code == 200, response.text
    assert response.json()["source_channel"] == channel
