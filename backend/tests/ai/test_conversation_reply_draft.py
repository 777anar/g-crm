"""Tests for AI draft generation (Phase 21 follow-through): a draft reply to
a Conversation via POST /ai/conversations/{id}/draft-reply -- draft-only,
never sent automatically."""


def test_draft_reply_creates_suggested_reply_recommendation(app_client, owner_headers, conversation):
    resp = app_client.post(
        f"/api/v1/ai/conversations/{conversation.id}/draft-reply", headers=owner_headers, json={}
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    rec = items[0]
    assert rec["recommendation_type"] == "suggested_reply"
    assert rec["analysis_kind"] == "conversation"
    assert rec["related_entity_type"] == "conversation"
    assert rec["related_entity_id"] == str(conversation.id)
    assert isinstance(rec["response"]["draft_reply"], str) and rec["response"]["draft_reply"]
    assert rec["response"]["reply_language"] in ("en", "az", "ru")


def test_draft_reply_never_sends_a_message(app_client, owner_headers, conversation, db_session):
    """The invariant this feature exists to prove: drafting never creates a
    real outbound Message -- only a human's own POST .../messages does."""
    from modules.communication.infrastructure.models.message import Message

    before = db_session.query(Message).count()
    app_client.post(f"/api/v1/ai/conversations/{conversation.id}/draft-reply", headers=owner_headers, json={})
    after = db_session.query(Message).count()
    assert after == before


def test_draft_reply_unknown_conversation_returns_404(app_client, owner_headers):
    import uuid

    resp = app_client.post(f"/api/v1/ai/conversations/{uuid.uuid4()}/draft-reply", headers=owner_headers, json={})
    assert resp.status_code == 404


def test_draft_reply_requires_write_permission(app_client, viewer_headers, conversation):
    resp = app_client.post(
        f"/api/v1/ai/conversations/{conversation.id}/draft-reply", headers=viewer_headers, json={}
    )
    assert resp.status_code == 403
