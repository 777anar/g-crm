"""Tests for inbound/outbound messages, unread counters, and the
provider abstraction (NullChannelProvider -- no real WhatsApp/Meta calls)."""


def test_inbound_message_creates_conversation_and_increments_unread(app_client, owner_headers, whatsapp_channel):
    resp = app_client.post(
        "/api/v1/communication/inbound",
        headers=owner_headers,
        json={
            "channel_id": whatsapp_channel["id"],
            "external_contact_id": "+994500001111",
            "external_contact_name": "New Contact",
            "body": "Hi, do you have Calacatta in stock?",
        },
    )
    assert resp.status_code == 200, resp.text
    message = resp.json()
    assert message["direction"] == "inbound"
    assert message["sender_type"] == "customer"
    assert message["status"] == "received"

    conversations = app_client.get("/api/v1/communication/conversations", headers=owner_headers).json()["items"]
    conv = next(c for c in conversations if c["external_contact_id"] == "+994500001111")
    assert conv["unread_count"] == 1
    assert conv["last_message_preview"] == "Hi, do you have Calacatta in stock?"


def test_multiple_inbound_messages_accumulate_unread(app_client, owner_headers, whatsapp_channel):
    for i in range(3):
        app_client.post(
            "/api/v1/communication/inbound",
            headers=owner_headers,
            json={
                "channel_id": whatsapp_channel["id"],
                "external_contact_id": "+994500002222",
                "body": f"Message {i}",
            },
        )
    conversations = app_client.get("/api/v1/communication/conversations", headers=owner_headers).json()["items"]
    conv = next(c for c in conversations if c["external_contact_id"] == "+994500002222")
    assert conv["unread_count"] == 3


def test_mark_conversation_read_resets_counter(app_client, owner_headers, whatsapp_channel):
    app_client.post(
        "/api/v1/communication/inbound",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500003333", "body": "Hello"},
    )
    conv = next(
        c for c in app_client.get("/api/v1/communication/conversations", headers=owner_headers).json()["items"]
        if c["external_contact_id"] == "+994500003333"
    )
    assert conv["unread_count"] == 1

    resp = app_client.post(f"/api/v1/communication/conversations/{conv['id']}/read", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0


def test_send_outbound_message_uses_null_provider(app_client, owner_headers, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500004444"},
    ).json()

    resp = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages",
        headers=owner_headers,
        json={"body": "Thanks for reaching out! How can I help?"},
    )
    assert resp.status_code == 200, resp.text
    message = resp.json()
    assert message["direction"] == "outbound"
    assert message["sender_type"] == "agent"
    assert message["status"] == "sent"
    # NullChannelProvider mints a "local-<uuid>" id rather than calling a
    # real WhatsApp/Meta API -- see infrastructure/providers/null_provider.py.
    assert message["external_message_id"].startswith("local-")

    conv_after = app_client.get(f"/api/v1/communication/conversations/{conv['id']}", headers=owner_headers).json()
    assert conv_after["last_message_preview"] == "Thanks for reaching out! How can I help?"


def test_cannot_send_via_inactive_channel(app_client, owner_headers, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500005555"},
    ).json()
    app_client.patch(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}", headers=owner_headers, json={"is_active": False}
    )

    resp = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages",
        headers=owner_headers,
        json={"body": "This should fail"},
    )
    assert resp.status_code == 422, resp.text


def test_list_messages_ordered_oldest_first(app_client, owner_headers, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500006666"},
    ).json()
    app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "First"}
    )
    app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Second"}
    )

    messages = app_client.get(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers
    ).json()["items"]
    assert [m["body"] for m in messages] == ["First", "Second"]


def test_reopens_closed_conversation_on_new_inbound_message(app_client, owner_headers, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500007777"},
    ).json()
    app_client.patch(
        f"/api/v1/communication/conversations/{conv['id']}", headers=owner_headers, json={"status": "closed"}
    )

    app_client.post(
        "/api/v1/communication/inbound",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500007777", "body": "I'm back"},
    )

    reloaded = app_client.get(f"/api/v1/communication/conversations/{conv['id']}", headers=owner_headers).json()
    assert reloaded["status"] == "open"


def test_invalid_message_type_returns_400(app_client, owner_headers, whatsapp_channel):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500008888"},
    ).json()
    resp = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages",
        headers=owner_headers,
        json={"body": "hi", "message_type": "carrier_pigeon"},
    )
    assert resp.status_code == 400, resp.text
