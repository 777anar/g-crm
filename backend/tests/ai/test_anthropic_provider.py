"""Unit tests for the real Anthropic provider (Phase 21). No network call is
ever made here -- the Anthropic SDK client is replaced with a small fake that
returns a canned structured-output response, so these tests are fast,
deterministic, and don't require a real ANTHROPIC_API_KEY."""
import json

import anthropic
import httpx
import pytest

from core.config import settings
from modules.ai.domain.exceptions import AIProviderNotConfiguredError, AIProviderUpstreamError
from modules.ai.infrastructure.providers.anthropic_provider import AnthropicProvider


class _FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeUsage:
    def __init__(self, input_tokens=100, output_tokens=50):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeMessage:
    def __init__(self, payload: dict, *, stop_reason="end_turn"):
        self.content = [_FakeTextBlock(json.dumps(payload))]
        self.usage = _FakeUsage()
        self.stop_reason = stop_reason


class _FakeMessagesResource:
    def __init__(self, response=None, error: Exception = None):
        self._response = response
        self._error = error
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error:
            raise self._error
        return self._response


class _FakeClient:
    def __init__(self, response=None, error: Exception = None):
        self.messages = _FakeMessagesResource(response=response, error=error)


@pytest.fixture(autouse=True)
def _configure_api_key(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key-not-real")
    yield


def _provider_with_fake_client(response=None, error=None) -> AnthropicProvider:
    provider = AnthropicProvider()
    provider._client = _FakeClient(response=response, error=error)
    return provider


def test_raises_not_configured_when_no_api_key(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    provider = AnthropicProvider()
    with pytest.raises(AIProviderNotConfiguredError):
        provider.analyze_lead(prompt="x", context={"lead": {"id": "1", "full_name": "A"}, "other_leads": [], "customers": []})


def test_analyze_lead_merges_llm_judgment_with_deterministic_matching():
    lead = {"id": "lead-1", "full_name": "Jane Doe", "email": "jane@example.com", "phone": None, "source_channel": "website"}
    other_leads = [{"id": "lead-2", "full_name": "Other", "email": "jane@example.com", "phone": None}]
    customers = [{"id": "cust-1", "name": "Jane D.", "email": None, "phone": None}]

    response = _FakeMessage({
        "score": 82, "win_probability": 0.7, "priority": "high",
        "next_best_action": "Call within the hour", "follow_up_due_in_days": 1,
        "follow_up_note": "Follow up with Jane Doe", "quality_explanation": "Strong signal from website source.",
        "confidence": 0.81,
    })
    provider = _provider_with_fake_client(response=response)

    result = provider.analyze_lead(prompt="analyze", context={"lead": lead, "other_leads": other_leads, "customers": customers})

    assert result.data["score"] == 82
    assert result.data["priority"] == "high"
    assert result.data["follow_up"] == {"due_in_days": 1, "note": "Follow up with Jane Doe"}
    # Deterministic exact-match fields, computed by analysis_helpers, not the model:
    assert result.data["duplicate_lead_ids"] == ["lead-2"]
    assert result.data["missing_fields"] == ["phone"]
    assert result.confidence == 0.81
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.cost_usd is not None
    assert result.raw_response is not None


def test_analyze_conversation_merges_extraction_and_link_suggestion():
    context = {
        "conversation": {"customer_id": None, "lead_id": None, "project_id": None, "quote_id": None, "order_id": None},
        "messages": [{"direction": "inbound", "body": "Contact me at buyer@example.com", "sender_type": "customer"}],
        "catalog_material_names": ["Calacatta Gold"],
        "matched_customer": {"id": "cust-9"},
    }
    response = _FakeMessage({
        "language": "en", "intent": "pricing_inquiry", "sentiment": "neutral", "urgency": "medium",
        "summary": "Customer asking about pricing.", "confidence": 0.66,
    })
    provider = _provider_with_fake_client(response=response)

    result = provider.analyze_conversation(prompt="analyze", context=context)

    assert result.data["intent"] == "pricing_inquiry"
    assert "buyer@example.com" in result.data["extracted"]["emails"]
    assert result.data["link_suggestion"] == {
        "entity_type": "customer", "entity_id": "cust-9",
        "reason": "Extracted contact details match an existing Customer record.",
    }


def test_analyze_quote_selects_only_real_candidates_and_drops_hallucinated_ids():
    top_materials = [
        {"material_id": "mat-1", "material_name": "Calacatta Gold", "count": 5, "avg_sale_price": 150.0},
        {"material_id": "mat-2", "material_name": "Nero Marquina", "count": 3, "avg_sale_price": 130.0},
    ]
    context = {
        "items": [], "top_materials": top_materials, "co_occurring_materials": [], "upsell_candidates": [],
        "avg_discount_pct": 5.0, "material_price_stats": {}, "section_item_count": 1, "total_area_m2": 5.0,
    }
    response = _FakeMessage({
        # "mat-999" does not exist in top_materials -- must be silently dropped, not fabricated.
        "product_recommendation_ids": ["mat-2", "mat-999", "mat-1"],
        "cross_sell_ids": [], "upsell_ids": [], "confidence": 0.6,
    })
    provider = _provider_with_fake_client(response=response)

    result = provider.analyze_quote(prompt="analyze", context=context)

    recommended_ids = [m["material_id"] for m in result.data["product_recommendations"]]
    assert recommended_ids == ["mat-2", "mat-1"]
    assert result.data["delivery_complexity"] == "low"


def test_suggest_tasks_drops_task_referencing_unknown_entity():
    context = {
        "stale_leads": [{"id": "lead-1", "full_name": "Jane"}],
        "stale_conversations": [],
        "user_workload": {"user-1": 2, "user-2": 0},
        "at_risk_tasks": [],
    }
    response = _FakeMessage({
        "tasks": [
            {"related_entity_type": "lead", "related_entity_id": "lead-1", "title": "Follow up with Jane", "priority": "high", "due_in_days": 1},
            {"related_entity_type": "lead", "related_entity_id": "lead-does-not-exist", "title": "Bogus", "priority": "low", "due_in_days": 3},
        ],
        "confidence": 0.5,
    })
    provider = _provider_with_fake_client(response=response)

    result = provider.suggest_tasks(prompt="suggest", context=context)

    assert len(result.data["tasks"]) == 1
    assert result.data["tasks"][0]["related_entity_id"] == "lead-1"
    assert result.data["assignee_suggestion"] == "user-2"


def test_upstream_rate_limit_error_is_mapped_to_domain_error():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(429, request=request)
    fake_error = anthropic.RateLimitError(message="rate limited", response=response, body=None)
    provider = _provider_with_fake_client(error=fake_error)
    with pytest.raises(AIProviderUpstreamError):
        provider.analyze_lead(prompt="x", context={"lead": {"id": "1", "full_name": "A"}, "other_leads": [], "customers": []})


def test_invalid_json_response_raises_upstream_error():
    bad_response = _FakeMessage.__new__(_FakeMessage)
    bad_response.content = [_FakeTextBlock("not valid json")]
    bad_response.usage = _FakeUsage()
    bad_response.stop_reason = "end_turn"
    provider = _provider_with_fake_client(response=bad_response)
    with pytest.raises(AIProviderUpstreamError):
        provider.analyze_lead(prompt="x", context={"lead": {"id": "1", "full_name": "A"}, "other_leads": [], "customers": []})


def test_refusal_stop_reason_raises_upstream_error():
    response = _FakeMessage({}, stop_reason="refusal")
    provider = _provider_with_fake_client(response=response)
    with pytest.raises(AIProviderUpstreamError):
        provider.analyze_lead(prompt="x", context={"lead": {"id": "1", "full_name": "A"}, "other_leads": [], "customers": []})
