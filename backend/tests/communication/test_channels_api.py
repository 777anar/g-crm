"""Tests for Channel configuration (WhatsApp/Instagram/Messenger/Email/SMS)."""


def test_create_channel(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "whatsapp", "display_name": "Support WhatsApp", "identifier": "+994551112233"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["channel_type"] == "whatsapp"
    assert body["is_active"] is True


def test_create_channel_requires_write_permission(app_client, viewer_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=viewer_headers,
        json={"channel_type": "email", "display_name": "Support Email"},
    )
    assert resp.status_code == 403


def test_create_channel_invalid_type_returns_400(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "carrier_pigeon", "display_name": "Nope"},
    )
    assert resp.status_code == 400, resp.text


def test_multiple_whatsapp_numbers_allowed(app_client, owner_headers):
    first = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "whatsapp", "display_name": "Sales WhatsApp", "identifier": "+994501111111"},
    )
    second = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "whatsapp", "display_name": "Support WhatsApp", "identifier": "+994502222222"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]

    resp = app_client.get(
        "/api/v1/communication/channels", headers=owner_headers, params={"channel_type": "whatsapp"}
    )
    assert len(resp.json()["items"]) == 2


def test_update_channel_deactivate(app_client, owner_headers, whatsapp_channel):
    resp = app_client.patch(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}",
        headers=owner_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False


def test_viewer_can_list_channels(app_client, owner_headers, viewer_headers, whatsapp_channel):
    resp = app_client.get("/api/v1/communication/channels", headers=viewer_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
