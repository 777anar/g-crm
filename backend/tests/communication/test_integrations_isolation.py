"""Multi-company isolation for the Version 2.9 real-integrations tables
(ChannelCredential, MessageQueueEntry, IntegrationLogEntry)."""
from core.auth.models import ROLE_OWNER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from tests.communication.conftest import configure_credential

WHATSAPP_CONFIG = {
    "phone_number_id": "1234567890", "access_token": "fake-token",
    "app_secret": "fake-secret", "verify_token": "fake-verify",
}


def _other_company_headers(db_session):
    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-integrations-test", enabled_modules=["communication"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@integrations.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    return {"Authorization": f"Bearer {token}"}


def test_credential_not_visible_from_other_company(app_client, owner_headers, whatsapp_channel, db_session):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    other_headers = _other_company_headers(db_session)

    resp = app_client.get(f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential", headers=other_headers)
    assert resp.status_code == 404


def test_other_company_cannot_configure_credential_on_foreign_channel(app_client, whatsapp_channel, db_session):
    other_headers = _other_company_headers(db_session)
    resp = app_client.put(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential",
        headers=other_headers,
        json={"provider": "meta_whatsapp", "config": WHATSAPP_CONFIG},
    )
    assert resp.status_code == 404


def test_queue_isolated_by_company(app_client, owner_headers, whatsapp_channel, mock_httpx_responses, db_session):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    conv = app_client.post(
        "/api/v1/communication/conversations", headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500066660"},
    ).json()
    mock_httpx_responses.append((500, {"error": "boom"}))
    app_client.post(f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "hi"})

    other_headers = _other_company_headers(db_session)
    queue = app_client.get("/api/v1/communication/queue", headers=other_headers).json()["items"]
    assert queue == []


def test_integration_logs_isolated_by_company(app_client, owner_headers, whatsapp_channel, mock_httpx_responses, db_session):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    mock_httpx_responses.append((200, {"display_phone_number": "+994501111111"}))
    app_client.post(f"/api/v1/communication/channels/{whatsapp_channel['id']}/test-connection", headers=owner_headers)

    other_headers = _other_company_headers(db_session)
    logs = app_client.get("/api/v1/communication/integration-logs", headers=other_headers).json()["items"]
    assert logs == []
