"""Tests for conversation creation, CRM identification, and auto-Lead
creation for unknown senders."""


def test_start_conversation_matches_known_customer(app_client, owner_headers, whatsapp_channel, known_customer):
    resp = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={
            "channel_id": whatsapp_channel["id"],
            "external_contact_id": known_customer.whatsapp,
            "external_contact_name": "Rashad",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["customer_id"] == str(known_customer.id)
    assert body["lead_id"] is None


def test_start_conversation_auto_creates_lead_for_unknown_sender(app_client, owner_headers, whatsapp_channel):
    resp = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={
            "channel_id": whatsapp_channel["id"],
            "external_contact_id": "+994509998877",
            "external_contact_name": "Unknown Sender",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["customer_id"] is None
    assert body["lead_id"] is not None

    leads = app_client.get("/api/v1/crm/leads", headers=owner_headers).json()["items"]
    assert any(l["id"] == body["lead_id"] for l in leads)
    matched = next(l for l in leads if l["id"] == body["lead_id"])
    assert matched["full_name"] == "Unknown Sender"
    assert matched["source_channel"] == "whatsapp"
    assert matched["phone"] == "+994509998877"


def test_starting_conversation_twice_returns_same_conversation(app_client, owner_headers, whatsapp_channel):
    first = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500000001"},
    ).json()
    second = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500000001"},
    ).json()
    assert first["id"] == second["id"]


def test_get_and_list_conversations(app_client, owner_headers, whatsapp_channel):
    created = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500000002"},
    ).json()

    get_resp = app_client.get(f"/api/v1/communication/conversations/{created['id']}", headers=owner_headers)
    assert get_resp.status_code == 200

    list_resp = app_client.get("/api/v1/communication/conversations", headers=owner_headers)
    assert any(c["id"] == created["id"] for c in list_resp.json()["items"])


def test_update_conversation_status_and_assignment(app_client, owner_headers, rep_user, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500000003"},
    ).json()

    resp = app_client.patch(
        f"/api/v1/communication/conversations/{conv['id']}",
        headers=owner_headers,
        json={"status": "pending", "assigned_to": str(rep_user.id), "tags": ["vip", "follow-up"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["assigned_to"] == str(rep_user.id)
    assert body["tags"] == ["vip", "follow-up"]


def test_update_conversation_invalid_status_returns_400(app_client, owner_headers, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500000004"},
    ).json()
    resp = app_client.patch(
        f"/api/v1/communication/conversations/{conv['id']}", headers=owner_headers, json={"status": "archived"}
    )
    assert resp.status_code == 400, resp.text


def test_update_conversation_unknown_assignee_returns_400(app_client, owner_headers, whatsapp_channel):
    import uuid

    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500000005"},
    ).json()
    resp = app_client.patch(
        f"/api/v1/communication/conversations/{conv['id']}",
        headers=owner_headers,
        json={"assigned_to": str(uuid.uuid4())},
    )
    assert resp.status_code == 400, resp.text


def test_link_conversation_to_project_quote_order(app_client, owner_headers, whatsapp_channel):
    import uuid

    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500000006"},
    ).json()

    project_id = str(uuid.uuid4())
    resp = app_client.patch(
        f"/api/v1/communication/conversations/{conv['id']}",
        headers=owner_headers,
        json={"project_id": project_id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["project_id"] == project_id


def test_conversations_require_read_permission(app_client, viewer_headers):
    resp = app_client.get("/api/v1/communication/conversations", headers=viewer_headers)
    assert resp.status_code == 200


def test_starting_conversation_requires_write_permission(app_client, viewer_headers, whatsapp_channel):
    resp = app_client.post(
        "/api/v1/communication/conversations",
        headers=viewer_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500000007"},
    )
    assert resp.status_code == 403
