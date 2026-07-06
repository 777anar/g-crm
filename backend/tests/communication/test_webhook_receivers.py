"""End-to-end tests for the public, signature-verified webhook endpoints --
GET/POST /webhooks/meta/{id}, POST /webhooks/twilio/{id}, POST
/webhooks/generic/{id}. None of these send an Authorization header: trust
comes entirely from each provider's signature scheme."""
import base64
import hashlib
import hmac
import json

from tests.communication.conftest import configure_credential

WHATSAPP_CONFIG = {
    "phone_number_id": "1234567890",
    "access_token": "fake-token",
    "app_secret": "meta-app-secret",
    "verify_token": "my-verify-token",
}

TWILIO_CONFIG = {"account_sid": "AC_fake", "auth_token": "twilio-auth-token", "from_number": "+15550001111"}

WEBHOOK_CONFIG = {"outbound_url": "https://partner.example.com/hook", "secret": "webhook-shared-secret"}


def _meta_signature(app_secret: str, raw_body: bytes) -> str:
    digest = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_meta_verification_handshake_success(app_client, owner_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    resp = app_client.get(
        f"/api/v1/communication/webhooks/meta/{whatsapp_channel['id']}",
        params={"hub.mode": "subscribe", "hub.verify_token": "my-verify-token", "hub.challenge": "12345"},
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_meta_verification_handshake_wrong_token_rejected(app_client, owner_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    resp = app_client.get(
        f"/api/v1/communication/webhooks/meta/{whatsapp_channel['id']}",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert resp.status_code == 403


def test_meta_webhook_creates_inbound_message(app_client, owner_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"profile": {"name": "Jane Doe"}, "wa_id": "+994500099999"}],
                    "messages": [{"from": "+994500099999", "id": "wamid.INBOUND1", "type": "text", "text": {"body": "Hi there"}}],
                },
            }],
        }],
    }
    raw_body = json.dumps(payload).encode()
    signature = _meta_signature(WHATSAPP_CONFIG["app_secret"], raw_body)

    resp = app_client.post(
        f"/api/v1/communication/webhooks/meta/{whatsapp_channel['id']}",
        content=raw_body,
        headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["created_messages"] == 1

    conversations = app_client.get("/api/v1/communication/conversations", headers=owner_headers).json()["items"]
    conv = next(c for c in conversations if c["external_contact_id"] == "+994500099999")
    assert conv["last_message_preview"] == "Hi there"


def test_meta_webhook_invalid_signature_rejected_and_no_message_created(app_client, owner_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "+994500088888", "id": "x", "type": "text", "text": {"body": "hi"}}]}}]}]}
    raw_body = json.dumps(payload).encode()

    resp = app_client.post(
        f"/api/v1/communication/webhooks/meta/{whatsapp_channel['id']}",
        content=raw_body,
        headers={"X-Hub-Signature-256": "sha256=wrongsignature", "Content-Type": "application/json"},
    )
    assert resp.status_code == 403

    conversations = app_client.get("/api/v1/communication/conversations", headers=owner_headers).json()["items"]
    assert not any(c["external_contact_id"] == "+994500088888" for c in conversations)


def test_meta_webhook_rejected_signature_is_logged(app_client, owner_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    raw_body = b'{"entry": []}'
    app_client.post(
        f"/api/v1/communication/webhooks/meta/{whatsapp_channel['id']}",
        content=raw_body,
        headers={"X-Hub-Signature-256": "sha256=bad", "Content-Type": "application/json"},
    )
    logs = app_client.get("/api/v1/communication/integration-logs", headers=owner_headers, params={"direction": "inbound"}).json()["items"]
    assert len(logs) == 1
    assert logs[0]["signature_valid"] is False
    assert logs[0]["success"] is False


def test_meta_webhook_status_update_marks_message_delivered(app_client, owner_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    conv = app_client.post(
        "/api/v1/communication/conversations", headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500077777"},
    ).json()
    mock_httpx_responses.append((200, {"messages": [{"id": "wamid.SENT1"}]}))
    message = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Hi"}
    ).json()
    assert message["status"] == "sent"

    payload = {"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.SENT1", "status": "delivered"}]}}]}]}
    raw_body = json.dumps(payload).encode()
    signature = _meta_signature(WHATSAPP_CONFIG["app_secret"], raw_body)
    resp = app_client.post(
        f"/api/v1/communication/webhooks/meta/{whatsapp_channel['id']}",
        content=raw_body, headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated_statuses"] == 1

    messages = app_client.get(f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers).json()["items"]
    assert next(m for m in messages if m["id"] == message["id"])["status"] == "delivered"


def test_twilio_webhook_creates_inbound_message(app_client, owner_headers, sms_channel):
    configure_credential(app_client, owner_headers, sms_channel["id"], provider="twilio_sms", config=TWILIO_CONFIG)
    url = "http://testserver/api/v1/communication/webhooks/twilio/" + sms_channel["id"]
    params = {"From": "+15559990000", "Body": "Need a quote"}
    data = url + "".join(k + params[k] for k in sorted(params))
    signature = base64.b64encode(hmac.new(TWILIO_CONFIG["auth_token"].encode(), data.encode(), hashlib.sha1).digest()).decode()

    resp = app_client.post(
        f"/api/v1/communication/webhooks/twilio/{sms_channel['id']}",
        data=params, headers={"X-Twilio-Signature": signature},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["created_messages"] == 1


def test_twilio_webhook_invalid_signature_rejected(app_client, owner_headers, sms_channel):
    configure_credential(app_client, owner_headers, sms_channel["id"], provider="twilio_sms", config=TWILIO_CONFIG)
    resp = app_client.post(
        f"/api/v1/communication/webhooks/twilio/{sms_channel['id']}",
        data={"From": "+15559990001", "Body": "hi"}, headers={"X-Twilio-Signature": "bogus"},
    )
    assert resp.status_code == 403


def test_generic_webhook_creates_inbound_message(app_client, owner_headers, webhook_channel):
    configure_credential(app_client, owner_headers, webhook_channel["id"], provider="webhook", config=WEBHOOK_CONFIG)
    payload = {"external_contact_id": "partner-user-42", "external_contact_name": "Partner User", "body": "Hello from partner"}
    raw_body = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(WEBHOOK_CONFIG["secret"].encode(), raw_body, hashlib.sha256).hexdigest()

    resp = app_client.post(
        f"/api/v1/communication/webhooks/generic/{webhook_channel['id']}",
        content=raw_body, headers={"X-Signature-256": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["created_messages"] == 1


def test_generic_webhook_invalid_signature_rejected(app_client, owner_headers, webhook_channel):
    configure_credential(app_client, owner_headers, webhook_channel["id"], provider="webhook", config=WEBHOOK_CONFIG)
    payload = {"external_contact_id": "x", "body": "hi"}
    raw_body = json.dumps(payload).encode()

    resp = app_client.post(
        f"/api/v1/communication/webhooks/generic/{webhook_channel['id']}",
        content=raw_body, headers={"X-Signature-256": "wrong", "Content-Type": "application/json"},
    )
    assert resp.status_code == 403


def test_webhook_events_appear_in_webhook_monitor(app_client, owner_headers, webhook_channel):
    configure_credential(app_client, owner_headers, webhook_channel["id"], provider="webhook", config=WEBHOOK_CONFIG)
    payload = {"external_contact_id": "x", "body": "hi"}
    raw_body = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(WEBHOOK_CONFIG["secret"].encode(), raw_body, hashlib.sha256).hexdigest()
    app_client.post(
        f"/api/v1/communication/webhooks/generic/{webhook_channel['id']}",
        content=raw_body, headers={"X-Signature-256": signature, "Content-Type": "application/json"},
    )

    logs = app_client.get(
        "/api/v1/communication/integration-logs", headers=owner_headers, params={"direction": "inbound"}
    ).json()["items"]
    assert len(logs) == 1
    assert logs[0]["direction"] == "inbound"
    assert logs[0]["provider"] == "webhook"
