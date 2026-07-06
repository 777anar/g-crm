"""POST /channels/{id}/imap-sync -- mocks ImapMailboxClient entirely (no
real IMAP server involved) to verify the sync use case creates inbound
Messages, extracts attachments via the core Documents pipeline, and
advances the sync cursor (imap_last_synced_uid)."""
from modules.communication.infrastructure.providers import imap_sync_client as imap_module
from modules.communication.infrastructure.providers.imap_sync_client import FetchedAttachment, FetchedEmail
from tests.communication.conftest import configure_credential

EMAIL_CONFIG = {
    "smtp_host": "smtp.example.com", "smtp_port": 587, "smtp_username": "u", "smtp_password": "p",
    "from_address": "support@example.com",
    "imap_host": "imap.example.com", "imap_port": 993, "imap_username": "u", "imap_password": "p",
    "imap_folder": "INBOX",
}


def _patch_fetch(monkeypatch, emails):
    def fake_fetch(self, *, since_uid):
        return [e for e in emails if since_uid is None or e.uid > since_uid]

    monkeypatch.setattr(imap_module.ImapMailboxClient, "fetch_new_messages", fake_fetch)


def test_imap_sync_creates_inbound_message(app_client, owner_headers, email_channel, monkeypatch):
    configure_credential(app_client, owner_headers, email_channel["id"], provider="smtp", config=EMAIL_CONFIG)
    _patch_fetch(monkeypatch, [
        FetchedEmail(uid=1, from_address="customer@example.com", from_name="A Customer", subject="Quote request", body="Please send a quote"),
    ])

    resp = app_client.post(f"/api/v1/communication/channels/{email_channel['id']}/imap-sync", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["synced_count"] == 1

    conversations = app_client.get("/api/v1/communication/conversations", headers=owner_headers).json()["items"]
    conv = next(c for c in conversations if c["external_contact_id"] == "customer@example.com")
    assert conv["last_message_preview"] == "Please send a quote"


def test_imap_sync_advances_cursor_and_skips_already_synced(app_client, owner_headers, email_channel, monkeypatch):
    configure_credential(app_client, owner_headers, email_channel["id"], provider="smtp", config=EMAIL_CONFIG)
    _patch_fetch(monkeypatch, [
        FetchedEmail(uid=1, from_address="a@example.com", from_name=None, subject="s1", body="first"),
        FetchedEmail(uid=2, from_address="b@example.com", from_name=None, subject="s2", body="second"),
    ])
    first = app_client.post(f"/api/v1/communication/channels/{email_channel['id']}/imap-sync", headers=owner_headers)
    assert first.json()["synced_count"] == 2

    # Second sync call only returns uid > 2 -- nothing new.
    second = app_client.post(f"/api/v1/communication/channels/{email_channel['id']}/imap-sync", headers=owner_headers)
    assert second.json()["synced_count"] == 0


def test_imap_sync_extracts_attachment_via_documents_pipeline(app_client, owner_headers, email_channel, monkeypatch):
    configure_credential(app_client, owner_headers, email_channel["id"], provider="smtp", config=EMAIL_CONFIG)
    _patch_fetch(monkeypatch, [
        FetchedEmail(
            uid=1, from_address="customer@example.com", from_name=None, subject="Photo", body="See attached",
            attachments=[FetchedAttachment(filename="site.jpg", content=b"fake-image-bytes", mime_type="image/jpeg")],
        ),
    ])
    resp = app_client.post(f"/api/v1/communication/channels/{email_channel['id']}/imap-sync", headers=owner_headers)
    assert resp.status_code == 200, resp.text

    conversations = app_client.get("/api/v1/communication/conversations", headers=owner_headers).json()["items"]
    conv = next(c for c in conversations if c["external_contact_id"] == "customer@example.com")
    messages = app_client.get(f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers).json()["items"]
    message = messages[0]
    attachments = app_client.get(
        f"/api/v1/communication/conversations/{conv['id']}/messages/{message['id']}/attachments", headers=owner_headers
    ).json()["items"]
    assert len(attachments) == 1
    assert attachments[0]["file_name"] == "site.jpg"


def test_imap_sync_requires_configured_credential(app_client, owner_headers, email_channel):
    resp = app_client.post(f"/api/v1/communication/channels/{email_channel['id']}/imap-sync", headers=owner_headers)
    assert resp.status_code == 404


def test_imap_sync_logged_to_integration_logs(app_client, owner_headers, email_channel, monkeypatch):
    configure_credential(app_client, owner_headers, email_channel["id"], provider="smtp", config=EMAIL_CONFIG)
    _patch_fetch(monkeypatch, [])
    app_client.post(f"/api/v1/communication/channels/{email_channel['id']}/imap-sync", headers=owner_headers)

    logs = app_client.get("/api/v1/communication/integration-logs", headers=owner_headers).json()["items"]
    assert any(entry["action"] == "imap_sync" for entry in logs)
