"""Multi-company isolation and audit/event verification for the
Communication Center module."""


def test_conversations_isolated_by_company(app_client, db_session, owner_headers, whatsapp_channel, company):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500011111"},
    ).json()

    other_company = Company(
        name="KORONA PREMIUM", slug="korona-premium-comm-test", enabled_modules=["communication"]
    )
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@comm.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = app_client.get(f"/api/v1/communication/conversations/{conv['id']}", headers=other_headers)
    assert response.status_code == 404

    other_company_conversations = app_client.get("/api/v1/communication/conversations", headers=other_headers).json()
    assert conv["id"] not in [c["id"] for c in other_company_conversations["items"]]

    # The other company can't even see the first company's channel, so it
    # can't be used to start a conversation there.
    channels = app_client.get("/api/v1/communication/channels", headers=other_headers).json()["items"]
    assert whatsapp_channel["id"] not in [c["id"] for c in channels]


def test_conversation_creation_writes_audit_and_event(
    app_client, owner_headers, db_session, owner_user, company, whatsapp_channel
):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500012222"},
    )

    entry = db_session.query(AuditLog).filter(AuditLog.action == "conversation.created").first()
    assert entry is not None
    assert entry.actor_user_id == owner_user.id
    assert entry.company_id == company.id
    assert entry.module == "communication"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "ConversationCreated" in events


def test_message_send_and_receive_write_audit_and_events(app_client, owner_headers, db_session, whatsapp_channel):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500013333"},
    ).json()
    app_client.post(
        f"/api/v1/communication/conversations/{conv['id']}/messages", headers=owner_headers, json={"body": "Hello!"}
    )
    app_client.post(
        "/api/v1/communication/inbound",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500013333", "body": "Reply"},
    )

    actions = [r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == "message").all()]
    assert "message.sent" in actions
    assert "message.received" in actions

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "MessageSent" in events
    assert "MessageReceived" in events


def test_channel_creation_writes_audit_and_event(app_client, owner_headers, db_session, company):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "email", "display_name": "Support Inbox"},
    )

    entry = db_session.query(AuditLog).filter(AuditLog.action == "channel.created").first()
    assert entry is not None
    assert entry.company_id == company.id

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "ChannelCreated" in events


def test_conversation_assignment_and_status_publish_distinct_events(
    app_client, owner_headers, rep_user, db_session, whatsapp_channel
):
    from core.events.models import EventLogEntry

    conv = app_client.post(
        "/api/v1/communication/conversations",
        headers=owner_headers,
        json={"channel_id": whatsapp_channel["id"], "external_contact_id": "+994500014444"},
    ).json()
    app_client.patch(
        f"/api/v1/communication/conversations/{conv['id']}",
        headers=owner_headers,
        json={"status": "pending", "assigned_to": str(rep_user.id)},
    )

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "ConversationStatusChanged" in events
    assert "ConversationAssigned" in events
