import uuid

import pytest


@pytest.mark.parametrize("channel", ["instagram", "facebook", "messenger", "whatsapp", "phone_call"])
def test_create_lead_for_each_channel(app_client, owner_headers, channel):
    response = app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={"full_name": f"Lead via {channel}", "source_channel": channel, "phone": "+994501112233"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_channel"] == channel
    assert body["status"] == "new"


def test_create_lead_invalid_channel_rejected(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={"full_name": "Bad Channel Lead", "source_channel": "tiktok"},
    )
    assert response.status_code in (400, 422)


def test_create_lead_requires_write_permission(app_client, viewer_headers):
    response = app_client.post(
        "/api/v1/crm/leads", headers=viewer_headers, json={"full_name": "Blocked Lead", "source_channel": "phone_call"}
    )
    assert response.status_code == 403


def test_list_leads_filter_by_channel(app_client, owner_headers):
    app_client.post(
        "/api/v1/crm/leads", headers=owner_headers, json={"full_name": "IG Lead", "source_channel": "instagram"}
    )
    app_client.post(
        "/api/v1/crm/leads", headers=owner_headers, json={"full_name": "FB Lead", "source_channel": "facebook"}
    )

    response = app_client.get("/api/v1/crm/leads", headers=owner_headers, params={"source_channel": "instagram"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(lead["source_channel"] == "instagram" for lead in items)
    assert any(lead["full_name"] == "IG Lead" for lead in items)


def test_get_lead_not_found(app_client, owner_headers):
    response = app_client.get(f"/api/v1/crm/leads/{uuid.uuid4()}", headers=owner_headers)
    assert response.status_code == 404


def test_convert_lead_creates_customer_and_contact(app_client, owner_headers):
    lead = app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={
            "full_name": "Convertible Lead",
            "source_channel": "whatsapp",
            "email": "lead@test.example",
            "campaign": "WhatsApp Promo",
        },
    ).json()

    response = app_client.post(f"/api/v1/crm/leads/{lead['id']}/convert", headers=owner_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["customer_id"]
    assert body["contact_id"]

    customer = app_client.get(f"/api/v1/crm/customers/{body['customer_id']}", headers=owner_headers).json()
    assert customer["name"] == "Convertible Lead"
    assert customer["lead_source"] == "whatsapp"
    assert customer["advertising_campaign"] == "WhatsApp Promo"

    lead_after = app_client.get(f"/api/v1/crm/leads/{lead['id']}", headers=owner_headers).json()
    assert lead_after["status"] == "converted"
    assert lead_after["converted_customer_id"] == body["customer_id"]


def test_convert_already_converted_lead_returns_conflict(app_client, owner_headers):
    lead = app_client.post(
        "/api/v1/crm/leads", headers=owner_headers, json={"full_name": "Double Convert", "source_channel": "phone_call"}
    ).json()
    app_client.post(f"/api/v1/crm/leads/{lead['id']}/convert", headers=owner_headers)

    response = app_client.post(f"/api/v1/crm/leads/{lead['id']}/convert", headers=owner_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
