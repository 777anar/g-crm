"""SendMessageUseCase with a real provider configured: success path (message
sent, logged) and failure path (message queued for retry, logged) -- via
POST /conversations/{id}/messages. The Null-provider default path is already
covered by test_messages_api.py::test_send_outbound_message_uses_null_provider,
unmodified, which is itself the backward-compatibility guarantee."""
from tests.communication.conftest import configure_credential

WHATSAPP_CONFIG = {
    "phone_number_id": "1234567890",
    "access_token": "fake-token",
    "app_secret": "fake-secret",
    "verify_token": "fake-verify",
}


def _start_conversation(app_client, headers, channel_id, contact_id):
    return app_client.post(
        "/api/v1/communication/conversations",
        headers=headers,
        json={"channel_id": channel_id, "external_contact_id": contact_id},
    ).json()


def test_send_via_real_provider_success(app_client, owner_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    conv = _start_conversation(app_client, owner_headers, whatsapp_channel["id"], "+994500011111")
    mock_httpx_responses.append((200, {"messages": [{"id": "wamid.HASH123"}]}))

    resp = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Hello!"}
    )
    assert resp.status_code == 200, resp.text
    message = resp.json()
    assert message["status"] == "sent"
    assert message["external_message_id"] == "wamid.HASH123"


def test_send_via_real_provider_failure_queues_for_retry(app_client, owner_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    conv = _start_conversation(app_client, owner_headers, whatsapp_channel["id"], "+994500022222")
    mock_httpx_responses.append((500, {"error": {"message": "internal error"}}))

    resp = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Hello!"}
    )
    # The API call itself never fails -- the message is recorded as failed
    # and queued for retry instead of a 500 reaching the agent.
    assert resp.status_code == 200, resp.text
    message = resp.json()
    assert message["status"] == "failed"

    queue = app_client.get("/api/v1/communication/queue", headers=owner_headers).json()["items"]
    matching = [q for q in queue if q["message_id"] == message["id"]]
    assert len(matching) == 1
    assert matching[0]["status"] == "pending"
    assert matching[0]["attempts"] == 0


def test_send_failure_logged_to_integration_logs(app_client, owner_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    conv = _start_conversation(app_client, owner_headers, whatsapp_channel["id"], "+994500033333")
    mock_httpx_responses.append((500, {"error": {"message": "boom"}}))

    app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Hi"}
    )
    logs = app_client.get("/api/v1/communication/integration-logs", headers=owner_headers).json()["items"]
    send_logs = [entry for entry in logs if entry["action"] == "send_message"]
    assert len(send_logs) == 1
    assert send_logs[0]["success"] is False
    assert send_logs[0]["error_message"] is not None


def test_send_success_logged_to_integration_logs(app_client, owner_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    conv = _start_conversation(app_client, owner_headers, whatsapp_channel["id"], "+994500044444")
    mock_httpx_responses.append((200, {"messages": [{"id": "wamid.OK"}]}))

    app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Hi"}
    )
    logs = app_client.get("/api/v1/communication/integration-logs", headers=owner_headers).json()["items"]
    send_logs = [entry for entry in logs if entry["action"] == "send_message"]
    assert len(send_logs) == 1
    assert send_logs[0]["success"] is True


def test_no_credential_still_uses_null_provider_and_logs_nothing(app_client, owner_headers, whatsapp_channel):
    """Direct regression guard for backward compatibility: a channel with
    no ChannelCredential configured must never create an integration log
    entry, since NullChannelProvider is a pure simulate-success stub."""
    conv = _start_conversation(app_client, owner_headers, whatsapp_channel["id"], "+994500055555")
    resp = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Hi"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"
    assert resp.json()["external_message_id"].startswith("local-")

    logs = app_client.get("/api/v1/communication/integration-logs", headers=owner_headers).json()["items"]
    assert logs == []
