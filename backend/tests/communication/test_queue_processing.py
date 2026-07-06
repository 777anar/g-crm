"""POST /queue/process -- retries due MessageQueueEntry rows. Tests
backdate `next_attempt_at` via db_session directly to simulate "enough time
has passed" without sleeping in the test."""
from datetime import datetime, timedelta, timezone

from modules.communication.infrastructure.models.message_queue_entry import MessageQueueEntry
from tests.communication.conftest import configure_credential

WHATSAPP_CONFIG = {
    "phone_number_id": "1234567890",
    "access_token": "fake-token",
    "app_secret": "fake-secret",
    "verify_token": "fake-verify",
}


def _queue_a_failed_send(app_client, owner_headers, whatsapp_channel, mock_httpx_responses, contact_id):
    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": contact_id},
    ).json()
    mock_httpx_responses.append((500, {"error": {"message": "boom"}}))
    message = app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Hi"}
    ).json()
    return message


def _make_due(db_session, message_id):
    entry = db_session.query(MessageQueueEntry).filter(MessageQueueEntry.message_id == message_id).one()
    entry.next_attempt_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    return entry


def test_queue_retry_succeeds(app_client, owner_headers, whatsapp_channel, mock_httpx_responses, db_session):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    message = _queue_a_failed_send(app_client, owner_headers, whatsapp_channel, mock_httpx_responses, "+994500111100")
    _make_due(db_session, message["id"])

    mock_httpx_responses.append((200, {"messages": [{"id": "wamid.RETRY_OK"}]}))
    resp = app_client.post("/api/v1/communication/queue/process", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["sent"] == 1
    assert result["failed"] == 0

    queue = app_client.get("/api/v1/communication/queue", headers=owner_headers).json()["items"]
    entry = next(q for q in queue if q["message_id"] == message["id"])
    assert entry["status"] == "sent"
    assert entry["attempts"] == 1


def test_queue_retry_failure_increments_attempts_and_reschedules(
    app_client, owner_headers, whatsapp_channel, mock_httpx_responses, db_session
):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    message = _queue_a_failed_send(app_client, owner_headers, whatsapp_channel, mock_httpx_responses, "+994500111101")
    _make_due(db_session, message["id"])

    mock_httpx_responses.append((500, {"error": {"message": "still down"}}))
    resp = app_client.post("/api/v1/communication/queue/process", headers=owner_headers)
    result = resp.json()
    assert result["still_pending"] == 1
    assert result["failed"] == 0

    queue = app_client.get("/api/v1/communication/queue", headers=owner_headers).json()["items"]
    entry = next(q for q in queue if q["message_id"] == message["id"])
    assert entry["status"] == "pending"
    assert entry["attempts"] == 1
    assert entry["next_attempt_at"] is not None


def test_queue_entry_marked_failed_after_max_attempts(
    app_client, owner_headers, whatsapp_channel, mock_httpx_responses, db_session
):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    message = _queue_a_failed_send(app_client, owner_headers, whatsapp_channel, mock_httpx_responses, "+994500111102")

    entry_row = db_session.query(MessageQueueEntry).filter(MessageQueueEntry.message_id == message["id"]).one()
    entry_row.max_attempts = 1
    db_session.commit()
    _make_due(db_session, message["id"])

    mock_httpx_responses.append((500, {"error": {"message": "still down"}}))
    resp = app_client.post("/api/v1/communication/queue/process", headers=owner_headers)
    result = resp.json()
    assert result["failed"] == 1

    queue = app_client.get("/api/v1/communication/queue", headers=owner_headers).json()["items"]
    entry = next(q for q in queue if q["message_id"] == message["id"])
    assert entry["status"] == "failed"

    message_after = app_client.get(
        f"/api/v1/communication/conversations/{message['conversation_id']}/messages", headers=owner_headers
    ).json()["items"]
    sent_message = next(m for m in message_after if m["id"] == message["id"])
    assert sent_message["status"] == "failed"


def test_not_yet_due_entries_are_not_processed(app_client, owner_headers, whatsapp_channel, mock_httpx_responses):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    _queue_a_failed_send(app_client, owner_headers, whatsapp_channel, mock_httpx_responses, "+994500111103")

    resp = app_client.post("/api/v1/communication/queue/process", headers=owner_headers)
    result = resp.json()
    assert result["processed"] == 0


def test_viewer_can_list_queue_but_not_process(app_client, owner_headers, viewer_headers, whatsapp_channel):
    resp = app_client.get("/api/v1/communication/queue", headers=viewer_headers)
    assert resp.status_code == 200
    resp = app_client.post("/api/v1/communication/queue/process", headers=viewer_headers)
    assert resp.status_code == 403
