"""CRM Intelligence: analyzes one Lead and produces independently
reviewable recommendations (score, win probability, priority, next best
action, follow-up, duplicate/similar detection, missing-info detection, and
a plain-language quality explanation) from a single provider call.

Reads CRM's Lead/Customer models directly (the same cross-module read
pattern Production/Installation/Finance/Communication all use) -- never
writes to them. See AIRecommendation's docstring for why accepting a
recommendation still never mutates the Lead automatically.
"""
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.ai.application.dtos import AnalyzeLeadInput
from modules.ai.application.use_cases._shared import RecommendationBuilder, run_provider
from modules.ai.domain import events as ai_events
from modules.ai.domain.value_objects import (
    ANALYSIS_KIND_LEAD,
    RECOMMENDATION_TYPE_DUPLICATE_LEAD,
    RECOMMENDATION_TYPE_FOLLOW_UP,
    RECOMMENDATION_TYPE_LEAD_QUALITY_EXPLANATION,
    RECOMMENDATION_TYPE_LEAD_SCORE,
    RECOMMENDATION_TYPE_MISSING_INFO,
    RECOMMENDATION_TYPE_NEXT_BEST_ACTION,
    RECOMMENDATION_TYPE_PRIORITY,
    RECOMMENDATION_TYPE_SIMILAR_CUSTOMER,
    RECOMMENDATION_TYPE_WIN_PROBABILITY,
)
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.providers.registry import get_provider
from modules.crm.infrastructure.models.customer import Customer
from modules.crm.infrastructure.models.lead import Lead

MODULE_NAME = "ai"


def _lead_to_dict(lead: Lead) -> dict:
    return {
        "id": str(lead.id),
        "full_name": lead.full_name,
        "email": lead.email,
        "phone": lead.phone,
        "source_channel": lead.source_channel,
        "campaign": lead.campaign,
    }


def _customer_to_dict(customer: Customer) -> dict:
    return {"id": str(customer.id), "name": customer.name, "email": customer.email, "phone": customer.phone}


class AnalyzeLeadUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, data: AnalyzeLeadInput) -> List[AIRecommendation]:
        lead = self.db.scalar(select(Lead).where(Lead.id == data.lead_id, Lead.company_id == data.company_id))
        if lead is None:
            raise NotFoundError("Lead not found")

        other_leads = list(self.db.scalars(
            select(Lead).where(Lead.company_id == data.company_id, Lead.id != lead.id).limit(200)
        ).all())
        customers = list(self.db.scalars(
            select(Customer).where(Customer.company_id == data.company_id, Customer.deleted_at.is_(None)).limit(200)
        ).all())

        context = {
            "lead": _lead_to_dict(lead),
            "other_leads": [_lead_to_dict(l) for l in other_leads],
            "customers": [_customer_to_dict(c) for c in customers],
        }
        prompt = (
            "Analyze this CRM lead for a stone/slab gallery business.\n"
            f"Name: {lead.full_name}\nSource: {lead.source_channel}\nCampaign: {lead.campaign or 'none'}\n"
            f"Email: {lead.email or 'none'}\nPhone: {lead.phone or 'none'}\n"
            "Return a lead score (0-100), win probability, priority, next best action, a follow-up "
            "recommendation, any duplicate leads or similar existing customers, missing contact fields, "
            "and a plain-language explanation of the score."
        )

        provider = get_provider(data.provider_name)
        timed = run_provider(provider.analyze_lead, prompt=prompt, context=context)
        d = timed.result.data

        builder = RecommendationBuilder(
            self.db,
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            analysis_kind=ANALYSIS_KIND_LEAD,
            related_entity_type="lead",
            related_entity_id=lead.id,
            provider=provider,
            prompt=prompt,
            confidence=timed.result.confidence,
            execution_time_ms=timed.execution_time_ms,
        )
        builder.add(RECOMMENDATION_TYPE_LEAD_SCORE, {"score": d["score"]}, f"Lead score: {d['score']}/100")
        builder.add(
            RECOMMENDATION_TYPE_WIN_PROBABILITY,
            {"win_probability": d["win_probability"]},
            f"Win probability: {round(d['win_probability'] * 100)}%",
        )
        builder.add(RECOMMENDATION_TYPE_PRIORITY, {"priority": d["priority"]}, f"Suggested priority: {d['priority']}")
        builder.add(
            RECOMMENDATION_TYPE_NEXT_BEST_ACTION, {"next_best_action": d["next_best_action"]}, d["next_best_action"]
        )
        builder.add(
            RECOMMENDATION_TYPE_FOLLOW_UP, d["follow_up"], f"Follow up in {d['follow_up']['due_in_days']} day(s)"
        )
        if d["duplicate_lead_ids"]:
            builder.add(
                RECOMMENDATION_TYPE_DUPLICATE_LEAD,
                {"duplicate_lead_ids": d["duplicate_lead_ids"]},
                f"{len(d['duplicate_lead_ids'])} possible duplicate lead(s)",
            )
        if d["similar_customer_ids"]:
            builder.add(
                RECOMMENDATION_TYPE_SIMILAR_CUSTOMER,
                {"similar_customer_ids": d["similar_customer_ids"]},
                f"{len(d['similar_customer_ids'])} similar existing customer(s)",
            )
        if d["missing_fields"]:
            builder.add(
                RECOMMENDATION_TYPE_MISSING_INFO,
                {"missing_fields": d["missing_fields"]},
                f"Missing: {', '.join(d['missing_fields'])}",
            )
        builder.add(
            RECOMMENDATION_TYPE_LEAD_QUALITY_EXPLANATION,
            {"explanation": d["quality_explanation"]},
            d["quality_explanation"],
        )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="ai.lead_analyzed",
            entity_type="lead",
            entity_id=lead.id,
            diff={"recommendation_count": len(builder.created), "provider": provider.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=ai_events.LEAD_ANALYZED,
                company_id=data.company_id,
                payload={"lead_id": str(lead.id), "recommendation_count": len(builder.created)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return builder.created
