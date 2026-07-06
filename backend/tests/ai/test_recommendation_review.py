"""Tests for the human-in-the-loop review gate: accept/reject/edit, and the
recommendations list/get endpoints."""


def _first_recommendation_id(app_client, owner_headers, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    return items[0]["id"]


def test_accept_recommendation(app_client, owner_headers, owner_user, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    resp = app_client.post(f"/api/v1/ai/recommendations/{rec_id}/review", headers=owner_headers, json={"decision": "accept"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["reviewed_by"] == str(owner_user.id)
    assert body["reviewed_at"] is not None


def test_reject_recommendation(app_client, owner_headers, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    resp = app_client.post(f"/api/v1/ai/recommendations/{rec_id}/review", headers=owner_headers, json={"decision": "reject"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_edit_recommendation_stores_edited_response(app_client, owner_headers, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    resp = app_client.post(
        f"/api/v1/ai/recommendations/{rec_id}/review",
        headers=owner_headers,
        json={"decision": "edit", "edited_response": {"score": 99}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "edited"
    assert body["edited_response"] == {"score": 99}


def test_accepting_underlying_recommendation_never_mutates_the_lead(app_client, owner_headers, lead):
    """The core safety property: review decisions only ever change the
    recommendation row itself."""
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    app_client.post(f"/api/v1/ai/recommendations/{rec_id}/review", headers=owner_headers, json={"decision": "accept"})

    leads = app_client.get("/api/v1/crm/leads", headers=owner_headers).json()["items"]
    reloaded = next(l for l in leads if l["id"] == lead["id"])
    assert reloaded == lead


def test_cannot_review_twice(app_client, owner_headers, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    app_client.post(f"/api/v1/ai/recommendations/{rec_id}/review", headers=owner_headers, json={"decision": "accept"})

    resp = app_client.post(f"/api/v1/ai/recommendations/{rec_id}/review", headers=owner_headers, json={"decision": "reject"})
    assert resp.status_code == 422, resp.text


def test_invalid_decision_value_returns_400(app_client, owner_headers, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    resp = app_client.post(
        f"/api/v1/ai/recommendations/{rec_id}/review", headers=owner_headers, json={"decision": "maybe"}
    )
    assert resp.status_code == 400, resp.text


def test_review_requires_write_permission(app_client, owner_headers, viewer_headers, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    resp = app_client.post(
        f"/api/v1/ai/recommendations/{rec_id}/review", headers=viewer_headers, json={"decision": "accept"}
    )
    assert resp.status_code == 403


def test_review_unknown_recommendation_returns_404(app_client, owner_headers):
    import uuid

    resp = app_client.post(
        f"/api/v1/ai/recommendations/{uuid.uuid4()}/review", headers=owner_headers, json={"decision": "accept"}
    )
    assert resp.status_code == 404


def test_list_recommendations_filters_by_status(app_client, owner_headers, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    app_client.post(f"/api/v1/ai/recommendations/{rec_id}/review", headers=owner_headers, json={"decision": "accept"})

    accepted = app_client.get("/api/v1/ai/recommendations", headers=owner_headers, params={"status": "accepted"}).json()["items"]
    assert any(r["id"] == rec_id for r in accepted)
    pending = app_client.get("/api/v1/ai/recommendations", headers=owner_headers, params={"status": "pending"}).json()["items"]
    assert not any(r["id"] == rec_id for r in pending)


def test_list_recommendations_filters_by_related_entity(app_client, owner_headers, lead):
    app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    items = app_client.get(
        "/api/v1/ai/recommendations",
        headers=owner_headers,
        params={"related_entity_type": "lead", "related_entity_id": lead["id"]},
    ).json()["items"]
    assert len(items) >= 5
    assert all(r["related_entity_id"] == lead["id"] for r in items)


def test_get_recommendation_by_id(app_client, owner_headers, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    resp = app_client.get(f"/api/v1/ai/recommendations/{rec_id}", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == rec_id


def test_get_unknown_recommendation_returns_404(app_client, owner_headers):
    import uuid

    resp = app_client.get(f"/api/v1/ai/recommendations/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


def test_viewer_can_list_and_read_recommendations(app_client, owner_headers, viewer_headers, lead):
    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    resp = app_client.get("/api/v1/ai/recommendations", headers=viewer_headers)
    assert resp.status_code == 200
    resp2 = app_client.get(f"/api/v1/ai/recommendations/{rec_id}", headers=viewer_headers)
    assert resp2.status_code == 200


def test_review_writes_audit_and_event(app_client, owner_headers, db_session, company, lead):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    rec_id = _first_recommendation_id(app_client, owner_headers, lead)
    app_client.post(f"/api/v1/ai/recommendations/{rec_id}/review", headers=owner_headers, json={"decision": "accept"})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "ai.recommendation_reviewed").first()
    assert entry is not None
    assert entry.company_id == company.id

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "RecommendationAccepted" in events
