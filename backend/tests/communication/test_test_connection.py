"""POST /channels/{id}/test-connection -- exercises the real provider's
test_connection() against a mocked HTTP layer (no real network calls) and
records health_status/last_error on the credential."""
from tests.communication.conftest import configure_credential

WHATSAPP_CONFIG = {
    "phone_number_id": "1234567890",
    "access_token": "fake-token",
    "app_secret": "fake-secret",
    "verify_token": "fake-verify",
}


def test_connection_success_sets_health_ok(app_client, owner_headers, rep_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    mock_httpx_responses.append((200, {"display_phone_number": "+994501111111"}))

    resp = app_client.post(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/test-connection", headers=rep_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["health_status"] == "ok"


def test_connection_failure_sets_health_error(app_client, owner_headers, rep_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    mock_httpx_responses.append((401, {"error": {"message": "Invalid OAuth access token"}}))

    resp = app_client.post(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/test-connection", headers=rep_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is False
    assert body["health_status"] == "error"


def test_connection_requires_configured_credential(app_client, rep_headers, whatsapp_channel):
    resp = app_client.post(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/test-connection", headers=rep_headers
    )
    assert resp.status_code == 404


def test_connection_result_persisted_on_credential(app_client, owner_headers, rep_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    mock_httpx_responses.append((200, {"display_phone_number": "+994501111111"}))
    app_client.post(f"/api/v1/communication/channels/{whatsapp_channel['id']}/test-connection", headers=rep_headers)

    resp = app_client.get(f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential", headers=owner_headers)
    assert resp.json()["health_status"] == "ok"
    assert resp.json()["last_checked_at"] is not None


def test_connection_logged_to_integration_logs(app_client, owner_headers, rep_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    mock_httpx_responses.append((200, {"display_phone_number": "+994501111111"}))
    app_client.post(f"/api/v1/communication/channels/{whatsapp_channel['id']}/test-connection", headers=rep_headers)

    resp = app_client.get("/api/v1/communication/integration-logs", headers=rep_headers)
    assert resp.status_code == 200
    actions = [item["action"] for item in resp.json()["items"]]
    assert "test_connection" in actions


def test_viewer_cannot_trigger_test_connection(app_client, owner_headers, viewer_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    resp = app_client.post(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/test-connection", headers=viewer_headers
    )
    assert resp.status_code == 403
