"""The first real `AIProvider` implementation (Phase 21: Real AI Provider
Integration), behind the exact same interface `MockAIProvider` implements --
no use case, DTO, schema, or frontend change was needed to add this class,
the same non-goal discipline Phase 7 held when Communication grew real
channel providers behind `ChannelProvider`.

Every method sends one structured-output request to the Claude Messages API
(`output_config.format`, a JSON Schema per analysis kind) so the model's
response is guaranteed-parseable JSON matching the exact dict shape the use
case expects -- the model is asked only for the genuinely language/judgment
half of each analysis (score, sentiment, phrasing, ranking within an
already-real candidate list); exact-id matching and financial-threshold math
are computed deterministically by `modules.ai.domain.analysis_helpers` and
merged in, so a hallucinated id or an approximated margin figure is
structurally impossible, not just unlikely.
"""
import json
from decimal import Decimal
from typing import Dict, List, Optional

import anthropic

from core.config import settings
from modules.ai.domain import analysis_helpers as helpers
from modules.ai.domain.exceptions import AIProviderNotConfiguredError, AIProviderUpstreamError
from modules.ai.infrastructure.providers.base import AIAnalysisResult, AIProvider

# USD per 1M tokens. Anthropic's published API pricing as of this
# integration -- update here if Anthropic reprices; there is no pricing
# endpoint to read this from at request time.
_PRICING_PER_MILLION_TOKENS = {
    "claude-opus-4-8": {"input": Decimal("5.00"), "output": Decimal("25.00")},
    "claude-opus-4-7": {"input": Decimal("5.00"), "output": Decimal("25.00")},
    "claude-sonnet-5": {"input": Decimal("3.00"), "output": Decimal("15.00")},
    "claude-haiku-4-5": {"input": Decimal("1.00"), "output": Decimal("5.00")},
}
_DEFAULT_PRICING = {"input": Decimal("5.00"), "output": Decimal("25.00")}

_MAX_TOKENS = 2048

_LEAD_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "win_probability": {"type": "number", "minimum": 0, "maximum": 1},
        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
        "next_best_action": {"type": "string"},
        "follow_up_due_in_days": {"type": "integer", "minimum": 0},
        "follow_up_note": {"type": "string"},
        "quality_explanation": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "score", "win_probability", "priority", "next_best_action",
        "follow_up_due_in_days", "follow_up_note", "quality_explanation", "confidence",
    ],
    "additionalProperties": False,
}

_CONVERSATION_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"type": "string", "description": "ISO 639-1 code, e.g. az/ru/en"},
        "intent": {
            "type": "string",
            "enum": ["pricing_inquiry", "availability_inquiry", "complaint", "order_status", "scheduling", "general_inquiry"],
        },
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
        "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
        "summary": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["language", "intent", "sentiment", "urgency", "summary", "confidence"],
    "additionalProperties": False,
}

_QUOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "product_recommendation_ids": {"type": "array", "items": {"type": "string"}},
        "cross_sell_ids": {"type": "array", "items": {"type": "string"}},
        "upsell_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["product_recommendation_ids", "cross_sell_ids", "upsell_ids", "confidence"],
    "additionalProperties": False,
}

_TASK_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "related_entity_type": {"type": "string", "enum": ["lead", "conversation"]},
        "related_entity_id": {"type": "string"},
        "title": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
        "due_in_days": {"type": "integer", "minimum": 0},
    },
    "required": ["related_entity_type", "related_entity_id", "title", "priority", "due_in_days"],
    "additionalProperties": False,
}

_TASKS_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {"type": "array", "items": _TASK_ITEM_SCHEMA},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["tasks", "confidence"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = (
    "You are the AI Sales Assistant embedded in G-STONE ERP, a stone/slab gallery "
    "business management system. You analyze CRM/sales data and return a single JSON "
    "object matching the provided schema exactly -- no prose outside the JSON. Every "
    "recommendation you produce is reviewed by a human before anything happens; you "
    "are not able to and must not claim to take any action yourself."
)


def _estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    pricing = _PRICING_PER_MILLION_TOKENS.get(model, _DEFAULT_PRICING)
    cost = (Decimal(input_tokens) * pricing["input"] + Decimal(output_tokens) * pricing["output"]) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.000001"))


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, *, model: Optional[str] = None):
        self.model = model or settings.anthropic_model
        self._client: Optional["anthropic.Anthropic"] = None

    def _get_client(self) -> "anthropic.Anthropic":
        if not settings.anthropic_api_key:
            raise AIProviderNotConfiguredError(
                "The 'anthropic' AI provider is registered but ANTHROPIC_API_KEY is not configured -- "
                "set it in the environment to enable real AI analysis, or use provider 'mock' until then."
            )
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def _call(self, *, user_prompt: str, schema: dict) -> tuple:
        """One structured-output request. Returns (data_without_confidence,
        confidence, AIAnalysisResult-shaped extras) -- factored out since all
        four analysis methods share this exact call/parse/error shape and
        differ only in prompt/schema/deterministic post-processing."""
        client = self._get_client()
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.AuthenticationError as exc:
            raise AIProviderNotConfiguredError("Anthropic rejected the configured API key (authentication failed).") from exc
        except anthropic.RateLimitError as exc:
            raise AIProviderUpstreamError("Anthropic API rate limit reached -- try again shortly.") from exc
        except anthropic.APIConnectionError as exc:
            raise AIProviderUpstreamError("Could not reach the Anthropic API.") from exc
        except anthropic.APIStatusError as exc:
            raise AIProviderUpstreamError(f"Anthropic API error: {exc.message}") from exc

        if response.stop_reason == "refusal":
            raise AIProviderUpstreamError("Anthropic declined to analyze this request.")

        text = next((block.text for block in response.content if block.type == "text"), "")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIProviderUpstreamError("Anthropic returned a response that was not valid JSON.") from exc

        confidence = float(parsed.pop("confidence", 0.7))
        usage = response.usage
        extras = {
            "raw_response": text,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": _estimate_cost_usd(self.model, usage.input_tokens, usage.output_tokens),
        }
        return parsed, confidence, extras

    # ── CRM Intelligence ─────────────────────────────────────────────────

    def analyze_lead(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        lead = context["lead"]
        parsed, confidence, extras = self._call(
            user_prompt=(
                f"{prompt}\n\nLead data (JSON): {json.dumps(lead)}\n"
                f"This company currently has {len(context.get('other_leads', []))} other lead(s) on file."
            ),
            schema=_LEAD_SCHEMA,
        )
        data = {
            "score": parsed["score"],
            "win_probability": parsed["win_probability"],
            "priority": parsed["priority"],
            "next_best_action": parsed["next_best_action"],
            "follow_up": {"due_in_days": parsed["follow_up_due_in_days"], "note": parsed["follow_up_note"]},
            "duplicate_lead_ids": helpers.find_duplicate_lead_ids(lead, context.get("other_leads", [])),
            "similar_customer_ids": helpers.find_similar_customer_ids(lead, context.get("customers", [])),
            "missing_fields": helpers.missing_contact_fields(lead),
            "quality_explanation": parsed["quality_explanation"],
        }
        return AIAnalysisResult(data=data, confidence=confidence, **extras)

    # ── Communication Intelligence ───────────────────────────────────────

    def analyze_conversation(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        messages: List[dict] = context.get("messages", [])
        parsed, confidence, extras = self._call(user_prompt=prompt, schema=_CONVERSATION_SCHEMA)
        extracted = helpers.extract_conversation_entities(messages, context.get("catalog_material_names", []))
        data = {
            "language": parsed["language"],
            "intent": parsed["intent"],
            "sentiment": parsed["sentiment"],
            "urgency": parsed["urgency"],
            "summary": parsed["summary"],
            "extracted": extracted,
            "link_suggestion": helpers.suggest_conversation_link(context=context),
        }
        return AIAnalysisResult(data=data, confidence=confidence, **extras)

    # ── Sales Intelligence ────────────────────────────────────────────────

    def analyze_quote(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        top_materials: List[dict] = context.get("top_materials", [])
        co_occurring: List[dict] = context.get("co_occurring_materials", [])
        upsell_candidates: List[dict] = context.get("upsell_candidates", [])
        items: List[dict] = context.get("items", [])
        material_price_stats: Dict[str, dict] = context.get("material_price_stats", {})

        candidate_summary = (
            f"Candidate additional products (pick up to 3 by material_id, ranked best first): {json.dumps(top_materials)}\n"
            f"Candidate cross-sell products (materials that co-occur with this quote's items in accepted quotes): {json.dumps(co_occurring)}\n"
            f"Candidate upsell products (same material type, meaningfully higher historical price): {json.dumps(upsell_candidates)}"
        )
        parsed, confidence, extras = self._call(user_prompt=f"{prompt}\n\n{candidate_summary}", schema=_QUOTE_SCHEMA)

        data = {
            "product_recommendations": helpers.select_candidates_by_id(top_materials, parsed["product_recommendation_ids"]),
            "cross_sell_suggestions": helpers.select_candidates_by_id(co_occurring, parsed["cross_sell_ids"]),
            "upsell_suggestions": helpers.select_candidates_by_id(upsell_candidates, parsed["upsell_ids"]),
            "discount_recommendation": helpers.compute_discount_recommendation(context.get("avg_discount_pct", 0.0)),
            "margin_risks": helpers.compute_margin_risks(items),
            "price_anomalies": helpers.compute_price_anomalies(items, material_price_stats),
            "delivery_complexity": helpers.compute_delivery_complexity(
                item_count=context.get("section_item_count", len(items)),
                total_area_m2=context.get("total_area_m2", 0.0),
            ),
        }
        return AIAnalysisResult(data=data, confidence=confidence, **extras)

    # ── Task Intelligence ─────────────────────────────────────────────────

    def suggest_tasks(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        stale_leads: List[dict] = context.get("stale_leads", [])
        stale_conversations: List[dict] = context.get("stale_conversations", [])
        workload: Dict[str, int] = context.get("user_workload", {})
        at_risk_tasks: List[dict] = context.get("at_risk_tasks", [])

        candidate_summary = (
            f"Stale leads eligible for a follow-up task (id/full_name): {json.dumps(stale_leads)}\n"
            f"Unanswered conversations eligible for a follow-up task (id/external_contact_name): {json.dumps(stale_conversations)}\n"
            "Only reference related_entity_id values from the lists above, using related_entity_type "
            "'lead' or 'conversation' respectively."
        )
        parsed, confidence, extras = self._call(user_prompt=f"{prompt}\n\n{candidate_summary}", schema=_TASKS_SCHEMA)

        valid_lead_ids = {l["id"] for l in stale_leads}
        valid_conversation_ids = {c["id"] for c in stale_conversations}
        tasks = [
            {
                "title": t["title"],
                "priority": t["priority"],
                "due_in_days": t["due_in_days"],
                "related_entity_type": t["related_entity_type"],
                "related_entity_id": t["related_entity_id"],
                "suggested_assignee": helpers.suggest_assignee(workload),
            }
            for t in parsed["tasks"]
            if (t["related_entity_type"] == "lead" and t["related_entity_id"] in valid_lead_ids)
            or (t["related_entity_type"] == "conversation" and t["related_entity_id"] in valid_conversation_ids)
        ]

        data = {
            "tasks": tasks,
            "reminders": helpers.compute_task_reminders(tasks),
            "assignee_suggestion": helpers.suggest_assignee(workload),
            "overdue_risks": helpers.compute_overdue_risks(at_risk_tasks),
        }
        return AIAnalysisResult(data=data, confidence=confidence, **extras)
