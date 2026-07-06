"""Communication Intelligence: analyzes one Conversation's message history
and produces language/intent/sentiment/urgency, a summary, extracted
contact details, and a suggestion to link it to a Lead/Customer/Project/
Quote/Order if it isn't linked yet.

Reads Communication's Conversation/Message models and CRM/Sales/Orders'
models directly (cross-module read, never write) -- the customer-matching
here is a light heuristic pass over the transcript, separate from
Communication's own channel-identity matching, which only ever runs once,
at conversation creation (see modules.communication's
GetOrCreateConversationUseCase).
"""
import re
import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.ai.application.dtos import AnalyzeConversationInput
from modules.ai.application.use_cases._shared import RecommendationBuilder, run_provider
from modules.ai.domain import events as ai_events
from modules.ai.domain.value_objects import (
    ANALYSIS_KIND_CONVERSATION,
    RECOMMENDATION_TYPE_CONVERSATION_EXTRACTION,
    RECOMMENDATION_TYPE_CONVERSATION_INTENT,
    RECOMMENDATION_TYPE_CONVERSATION_LANGUAGE,
    RECOMMENDATION_TYPE_CONVERSATION_LINK,
    RECOMMENDATION_TYPE_CONVERSATION_SENTIMENT,
    RECOMMENDATION_TYPE_CONVERSATION_SUMMARY,
    RECOMMENDATION_TYPE_CONVERSATION_URGENCY,
)
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.providers.registry import get_provider
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.communication.infrastructure.models.conversation import Conversation
from modules.communication.infrastructure.models.message import Message
from modules.crm.infrastructure.models.customer import Customer
from modules.orders.infrastructure.models.order import Order
from modules.sales.infrastructure.models.project import Project
from modules.sales.infrastructure.models.quote import Quote

MODULE_NAME = "ai"
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


class AnalyzeConversationUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, data: AnalyzeConversationInput) -> List[AIRecommendation]:
        conversation = self.db.scalar(
            select(Conversation).where(
                Conversation.id == data.conversation_id, Conversation.company_id == data.company_id
            )
        )
        if conversation is None:
            raise NotFoundError("Conversation not found")

        messages = list(self.db.scalars(
            select(Message)
            .where(Message.company_id == data.company_id, Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
        ).all())

        material_names = list(self.db.scalars(
            select(StoneMaterial.name).where(StoneMaterial.company_id == data.company_id).limit(500)
        ).all())

        context = {
            "conversation": {
                "customer_id": str(conversation.customer_id) if conversation.customer_id else None,
                "lead_id": str(conversation.lead_id) if conversation.lead_id else None,
                "project_id": str(conversation.project_id) if conversation.project_id else None,
                "quote_id": str(conversation.quote_id) if conversation.quote_id else None,
                "order_id": str(conversation.order_id) if conversation.order_id else None,
            },
            "messages": [{"direction": m.direction, "body": m.body, "sender_type": m.sender_type} for m in messages],
            "catalog_material_names": material_names,
        }

        text_blob = "\n".join(m.body or "" for m in messages)
        matched_customer_id = conversation.customer_id
        if not matched_customer_id:
            emails_in_text = _EMAIL_RE.findall(text_blob)
            candidate = self.db.scalar(
                select(Customer).where(
                    Customer.company_id == data.company_id,
                    Customer.deleted_at.is_(None),
                    (Customer.email.in_(emails_in_text) if emails_in_text else False)
                    | (Customer.phone == conversation.external_contact_id)
                    | (Customer.whatsapp == conversation.external_contact_id),
                )
            )
            if candidate:
                matched_customer_id = candidate.id
                context["matched_customer"] = {"id": str(candidate.id)}

        if matched_customer_id:
            recent_project = self.db.scalar(
                select(Project)
                .where(Project.company_id == data.company_id, Project.customer_id == matched_customer_id)
                .order_by(Project.created_at.desc())
            )
            recent_quote = self.db.scalar(
                select(Quote)
                .where(Quote.company_id == data.company_id, Quote.customer_id == matched_customer_id)
                .order_by(Quote.created_at.desc())
            )
            recent_order = self.db.scalar(
                select(Order)
                .where(Order.company_id == data.company_id, Order.customer_id == matched_customer_id)
                .order_by(Order.created_at.desc())
            )
            if recent_project:
                context["recent_project_id"] = str(recent_project.id)
            if recent_quote:
                context["recent_quote_id"] = str(recent_quote.id)
            if recent_order:
                context["recent_order_id"] = str(recent_order.id)

        prompt = (
            "Analyze this customer conversation for a stone/slab gallery business.\n"
            f"Message count: {len(messages)}\n"
            + "\n".join(f"[{m.direction}] {m.body}" for m in messages[-20:])
            + "\nDetect language, intent, sentiment, urgency; summarize; extract contact details and product "
            "names; and suggest a CRM record to link this conversation to if it isn't linked yet."
        )

        provider = get_provider(data.provider_name)
        timed = run_provider(provider.analyze_conversation, prompt=prompt, context=context)
        d = timed.result.data

        builder = RecommendationBuilder(
            self.db,
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            analysis_kind=ANALYSIS_KIND_CONVERSATION,
            related_entity_type="conversation",
            related_entity_id=conversation.id,
            provider=provider,
            prompt=prompt,
            confidence=timed.result.confidence,
            execution_time_ms=timed.execution_time_ms,
        )
        builder.add(RECOMMENDATION_TYPE_CONVERSATION_LANGUAGE, {"language": d["language"]}, f"Language: {d['language']}")
        builder.add(
            RECOMMENDATION_TYPE_CONVERSATION_INTENT,
            {"intent": d["intent"]},
            f"Intent: {d['intent'].replace('_', ' ')}",
        )
        builder.add(
            RECOMMENDATION_TYPE_CONVERSATION_SENTIMENT, {"sentiment": d["sentiment"]}, f"Sentiment: {d['sentiment']}"
        )
        builder.add(RECOMMENDATION_TYPE_CONVERSATION_URGENCY, {"urgency": d["urgency"]}, f"Urgency: {d['urgency']}")
        builder.add(RECOMMENDATION_TYPE_CONVERSATION_SUMMARY, {"summary": d["summary"]}, d["summary"])

        extracted = d["extracted"]
        if any(extracted.values()):
            total_extracted = sum(len(v) for v in extracted.values())
            builder.add(
                RECOMMENDATION_TYPE_CONVERSATION_EXTRACTION, extracted, f"Extracted {total_extracted} detail(s)"
            )

        if d["link_suggestion"]:
            link = d["link_suggestion"]
            builder.add(
                RECOMMENDATION_TYPE_CONVERSATION_LINK,
                link,
                f"Suggest linking to {link['entity_type']}",
                related_entity_type=link["entity_type"],
                related_entity_id=uuid.UUID(link["entity_id"]),
            )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="ai.conversation_analyzed",
            entity_type="conversation",
            entity_id=conversation.id,
            diff={"recommendation_count": len(builder.created), "provider": provider.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=ai_events.CONVERSATION_ANALYZED,
                company_id=data.company_id,
                payload={"conversation_id": str(conversation.id), "recommendation_count": len(builder.created)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return builder.created
