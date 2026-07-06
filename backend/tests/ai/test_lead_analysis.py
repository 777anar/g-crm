"""Tests for CRM Intelligence: AnalyzeLeadUseCase / POST /ai/leads/{id}/analyze."""


def _types(items):
    return [r["recommendation_type"] for r in items]


def test_analyze_lead_returns_expected_recommendation_types(app_client, owner_headers, lead):
    resp = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    types = _types(items)
    for expected in (
        "lead_score", "win_probability", "priority_recommendation",
        "next_best_action", "follow_up_recommendation", "lead_quality_explanation",
    ):
        assert expected in types


def test_lead_score_within_bounds(app_client, owner_headers, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    score_rec = next(r for r in items if r["recommendation_type"] == "lead_score")
    assert 0 <= score_rec["response"]["score"] <= 100


def test_win_probability_within_bounds(app_client, owner_headers, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "win_probability")
    assert 0.0 <= rec["response"]["win_probability"] <= 1.0


def test_priority_is_valid_value(app_client, owner_headers, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "priority_recommendation")
    assert rec["response"]["priority"] in ("low", "medium", "high", "urgent")


def test_missing_info_detected_for_bare_lead(app_client, owner_headers, bare_lead):
    items = app_client.post(f"/api/v1/ai/leads/{bare_lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "missing_info")
    assert "email" in rec["response"]["missing_fields"]
    assert "phone" in rec["response"]["missing_fields"]


def test_missing_info_absent_for_complete_lead(app_client, owner_headers, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    assert "missing_info" not in _types(items)


def test_duplicate_lead_detected(app_client, owner_headers, lead):
    app_client.post(
        "/api/v1/crm/leads",
        headers=owner_headers,
        json={"full_name": "Rashad A.", "source_channel": "instagram", "email": lead["email"]},
    )
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "duplicate_lead")
    assert len(rec["response"]["duplicate_lead_ids"]) == 1


def test_similar_customer_detected(app_client, owner_headers, lead, customer, db_session):
    # Re-use the customer fixture's contact details on this lead so a match exists.
    from modules.crm.infrastructure.models.lead import Lead

    lead_row = db_session.get(Lead, lead["id"])
    lead_row.email = customer.email
    db_session.commit()

    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "similar_customer")
    assert str(customer.id) in rec["response"]["similar_customer_ids"]


def test_analyze_unknown_lead_returns_404(app_client, owner_headers):
    import uuid

    resp = app_client.post(f"/api/v1/ai/leads/{uuid.uuid4()}/analyze", headers=owner_headers, json={})
    assert resp.status_code == 404


def test_analyze_lead_requires_write_permission(app_client, viewer_headers, lead):
    resp = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=viewer_headers, json={})
    assert resp.status_code == 403


def test_recommendation_stores_full_audit_fields(app_client, owner_headers, owner_user, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    rec = items[0]
    assert rec["provider"] == "mock"
    assert rec["model"] == "mock-heuristic-v1"
    assert "Rashad Aliyev" in rec["prompt"]
    assert rec["response"]
    assert 0.0 <= rec["confidence_score"] <= 1.0
    assert rec["execution_time_ms"] >= 0
    assert rec["requested_by"] == str(owner_user.id)
    assert rec["status"] == "pending"
    assert rec["created_at"]


def test_analyze_lead_with_explicit_mock_provider(app_client, owner_headers, lead):
    resp = app_client.post(
        f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={"provider": "mock"}
    )
    assert resp.status_code == 200
    assert all(r["provider"] == "mock" for r in resp.json()["items"])


def test_analyze_lead_with_invalid_provider_returns_400(app_client, owner_headers, lead):
    resp = app_client.post(
        f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={"provider": "not-a-real-provider"}
    )
    assert resp.status_code == 400, resp.text


def test_analyze_lead_with_unimplemented_real_provider_falls_back_to_mock(app_client, owner_headers, lead):
    """openai/anthropic/gemini/ollama/azure_openai are valid, named provider
    slots -- see registry.py -- but none has a real implementation yet, so
    they currently resolve to the same MockAIProvider as "mock" itself."""
    resp = app_client.post(
        f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={"provider": "openai"}
    )
    assert resp.status_code == 200, resp.text
    assert all(r["provider"] == "mock" for r in resp.json()["items"])
