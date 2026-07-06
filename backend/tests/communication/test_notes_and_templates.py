"""Tests for internal conversation notes and message templates/quick replies."""


def test_add_and_list_conversation_note(app_client, owner_headers, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500009999"},
    ).json()

    resp = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/notes",
        headers=owner_headers,
        json={"body": "Customer wants a bulk discount -- escalate to manager."},
    )
    assert resp.status_code == 200, resp.text

    notes = app_client.get(f"/api/v1/communication/conversations/{conv['id']}/notes", headers=owner_headers).json()[
        "items"
    ]
    assert len(notes) == 1
    assert notes[0]["body"] == "Customer wants a bulk discount -- escalate to manager."


def test_notes_require_write_permission(app_client, viewer_headers, owner_headers, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500010000"},
    ).json()
    resp = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/notes", headers=viewer_headers, json={"body": "nope"}
    )
    assert resp.status_code == 403


def test_create_and_list_message_template(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/templates",
        headers=owner_headers,
        json={"name": "Greeting", "body": "Hi! Thanks for reaching out to G-STONE GALLERY.", "shortcut": "hello"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["channel_type"] is None

    templates = app_client.get("/api/v1/communication/templates", headers=owner_headers).json()["items"]
    assert len(templates) == 1


def test_channel_specific_template_filtering(app_client, owner_headers):
    app_client.post(
        "/api/v1/communication/templates",
        headers=owner_headers,
        json={"name": "WhatsApp-only", "body": "Only for WhatsApp", "channel_type": "whatsapp"},
    )
    app_client.post(
        "/api/v1/communication/templates",
        headers=owner_headers,
        json={"name": "Any channel", "body": "Works everywhere"},
    )

    resp = app_client.get(
        "/api/v1/communication/templates", headers=owner_headers, params={"channel_type": "whatsapp"}
    )
    names = [t["name"] for t in resp.json()["items"]]
    assert "WhatsApp-only" in names
    assert "Any channel" in names

    resp2 = app_client.get(
        "/api/v1/communication/templates", headers=owner_headers, params={"channel_type": "email"}
    )
    names2 = [t["name"] for t in resp2.json()["items"]]
    assert "WhatsApp-only" not in names2
    assert "Any channel" in names2


def test_update_template_deactivate(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/communication/templates",
        headers=owner_headers,
        json={"name": "Old Template", "body": "Outdated wording"},
    ).json()

    resp = app_client.patch(
        f"/api/v1/communication/templates/{created['id']}", headers=owner_headers, json={"is_active": False}
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_create_template_invalid_channel_type_returns_400(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/templates",
        headers=owner_headers,
        json={"name": "Bad", "body": "x", "channel_type": "carrier_pigeon"},
    )
    assert resp.status_code == 400, resp.text


def test_templates_require_write_permission(app_client, viewer_headers):
    resp = app_client.post(
        "/api/v1/communication/templates", headers=viewer_headers, json={"name": "Nope", "body": "x"}
    )
    assert resp.status_code == 403
