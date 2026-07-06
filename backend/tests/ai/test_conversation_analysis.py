"""Tests for Communication Intelligence: AnalyzeConversationUseCase /
POST /ai/conversations/{id}/analyze."""


def _types(items):
    return [r["recommendation_type"] for r in items]


def test_analyze_conversation_returns_expected_types(app_client, owner_headers, conversation):
    resp = app_client.post(f"/api/v1/ai/conversations/{conversation.id}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 200, resp.text
    types = _types(resp.json()["items"])
    for expected in (
        "conversation_language", "conversation_intent", "conversation_sentiment",
        "conversation_urgency", "conversation_summary",
    ):
        assert expected in types


def test_urgency_detected_as_high(app_client, owner_headers, conversation):
    items = app_client.post(f"/api/v1/ai/conversations/{conversation.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "conversation_urgency")
    assert rec["response"]["urgency"] == "high"


def test_intent_detected_as_pricing(app_client, owner_headers, conversation):
    items = app_client.post(f"/api/v1/ai/conversations/{conversation.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "conversation_intent")
    assert rec["response"]["intent"] == "pricing_inquiry"


def test_language_defaults_to_english(app_client, owner_headers, conversation):
    items = app_client.post(f"/api/v1/ai/conversations/{conversation.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "conversation_language")
    assert rec["response"]["language"] == "en"


def test_extraction_finds_email(app_client, owner_headers, conversation):
    items = app_client.post(f"/api/v1/ai/conversations/{conversation.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "conversation_extraction")
    assert "buyer@example.com" in rec["response"]["emails"]


def test_link_suggestion_when_extracted_email_matches_existing_customer(
    app_client, owner_headers, db_session, company, channel
):
    from modules.communication.infrastructure.models.conversation import Conversation
    from modules.communication.infrastructure.models.message import Message
    from modules.crm.infrastructure.models.customer import Customer

    matching_customer = Customer(company_id=company.id, name="Buyer Co", status="approved", type="business", email="buyer2@example.com")
    db_session.add(matching_customer)
    db_session.flush()

    conv = Conversation(company_id=company.id, channel_id=channel["id"], external_contact_id="+994500000099", status="open")
    db_session.add(conv)
    db_session.flush()
    db_session.add(Message(
        company_id=company.id, conversation_id=conv.id, direction="inbound", sender_type="customer",
        message_type="text", body="You can reach me at buyer2@example.com", status="received",
    ))
    db_session.commit()

    items = app_client.post(f"/api/v1/ai/conversations/{conv.id}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "conversation_link_suggestion")
    assert rec["response"]["entity_type"] == "customer"
    assert rec["response"]["entity_id"] == str(matching_customer.id)
    assert rec["related_entity_type"] == "customer"
    assert rec["related_entity_id"] == str(matching_customer.id)


def test_no_link_suggestion_when_already_linked_and_no_recent_records(app_client, owner_headers, db_session, company, channel, customer):
    from modules.communication.infrastructure.models.conversation import Conversation

    conv = Conversation(
        company_id=company.id, channel_id=channel["id"], external_contact_id="+994500000088",
        customer_id=customer.id, status="open",
    )
    db_session.add(conv)
    db_session.commit()

    items = app_client.post(f"/api/v1/ai/conversations/{conv.id}/analyze", headers=owner_headers, json={}).json()["items"]
    assert "conversation_link_suggestion" not in _types(items)


def test_analyze_unknown_conversation_returns_404(app_client, owner_headers):
    import uuid

    resp = app_client.post(f"/api/v1/ai/conversations/{uuid.uuid4()}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 404


def test_analyze_conversation_requires_write_permission(app_client, viewer_headers, conversation):
    resp = app_client.post(f"/api/v1/ai/conversations/{conversation.id}/analyze", headers=viewer_headers, json={})
    assert resp.status_code == 403


def test_analyze_conversation_writes_audit_and_event(app_client, owner_headers, db_session, company, conversation):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post(f"/api/v1/ai/conversations/{conversation.id}/analyze", headers=owner_headers, json={})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "ai.conversation_analyzed").first()
    assert entry is not None
    assert entry.company_id == company.id
    assert entry.module == "ai"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "ConversationAnalyzed" in events
