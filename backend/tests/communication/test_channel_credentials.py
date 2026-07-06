"""Channel credential configuration: RBAC (owner-only write, manager-tier
read), provider/channel_type validation, and secret masking."""
from tests.communication.conftest import configure_credential

WHATSAPP_CONFIG = {
    "phone_number_id": "1234567890",
    "access_token": "EAAG_fake_access_token_value",
    "app_secret": "fake_app_secret",
    "verify_token": "fake_verify_token",
}


def test_owner_can_configure_credential(app_client, owner_headers, whatsapp_channel):
    credential = configure_credential(
        app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG
    )
    assert credential["provider"] == "meta_whatsapp"
    assert credential["health_status"] == "unknown"


def test_configured_secret_is_masked_in_response(app_client, owner_headers, whatsapp_channel):
    credential = configure_credential(
        app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG
    )
    assert credential["masked_config"]["access_token"] != WHATSAPP_CONFIG["access_token"]
    assert credential["masked_config"]["access_token"].endswith(WHATSAPP_CONFIG["access_token"][-4:])
    assert "••••" in credential["masked_config"]["access_token"]
    # Non-secret fields are shown in full -- useful for verifying config.
    assert credential["masked_config"]["phone_number_id"] == WHATSAPP_CONFIG["phone_number_id"]


def test_manager_can_read_credential(app_client, owner_headers, manager_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    resp = app_client.get(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential", headers=manager_headers
    )
    assert resp.status_code == 200, resp.text


def test_rep_cannot_read_credential(app_client, owner_headers, rep_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    resp = app_client.get(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential", headers=rep_headers
    )
    assert resp.status_code == 403


def test_manager_cannot_configure_credential(app_client, manager_headers, whatsapp_channel):
    resp = app_client.put(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential",
        headers=manager_headers,
        json={"provider": "meta_whatsapp", "config": WHATSAPP_CONFIG},
    )
    assert resp.status_code == 403


def test_owner_only_can_configure_credential_rep_forbidden(app_client, rep_headers, whatsapp_channel):
    resp = app_client.put(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential",
        headers=rep_headers,
        json={"provider": "meta_whatsapp", "config": WHATSAPP_CONFIG},
    )
    assert resp.status_code == 403


def test_provider_must_match_channel_type(app_client, owner_headers, whatsapp_channel):
    resp = app_client.put(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential",
        headers=owner_headers,
        json={"provider": "twilio_sms", "config": {"account_sid": "AC123", "auth_token": "x", "from_number": "+1"}},
    )
    assert resp.status_code == 400, resp.text


def test_invalid_provider_name_rejected(app_client, owner_headers, whatsapp_channel):
    resp = app_client.put(
        f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential",
        headers=owner_headers,
        json={"provider": "not_a_real_provider", "config": {}},
    )
    assert resp.status_code == 400, resp.text


def test_get_credential_404_when_none_configured(app_client, owner_headers, whatsapp_channel):
    resp = app_client.get(f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential", headers=owner_headers)
    assert resp.status_code == 404


def test_owner_can_remove_credential(app_client, owner_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    resp = app_client.delete(f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential", headers=owner_headers)
    assert resp.status_code == 200, resp.text

    resp = app_client.get(f"/api/v1/communication/channels/{whatsapp_channel['id']}/credential", headers=owner_headers)
    assert resp.status_code == 404


def test_reconfiguring_resets_health_status_to_unknown(app_client, owner_headers, whatsapp_channel):
    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    updated_config = dict(WHATSAPP_CONFIG, access_token="a-new-token-value")
    credential = configure_credential(
        app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=updated_config
    )
    assert credential["health_status"] == "unknown"


def test_audit_log_never_contains_raw_secret_value(app_client, owner_headers, whatsapp_channel, db_session):
    from core.audit.models import AuditLog

    configure_credential(app_client, owner_headers, whatsapp_channel["id"], provider="meta_whatsapp", config=WHATSAPP_CONFIG)
    entries = db_session.query(AuditLog).filter(AuditLog.action == "channel.credential_configured").all()
    assert len(entries) == 1
    diff_text = str(entries[0].diff_json)
    assert WHATSAPP_CONFIG["access_token"] not in diff_text
    assert WHATSAPP_CONFIG["app_secret"] not in diff_text
