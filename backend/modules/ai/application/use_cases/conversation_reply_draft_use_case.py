"""AI draft generation (Phase 21 follow-through): a draft reply to a
Conversation's transcript, created as a single `suggested_reply`
recommendation. Draft-only -- a human copies the text into the compose box,
edits it, and sends it themselves through Communication's existing
send-message action; this use case never calls that action itself, keeping
"AI never performs a business action automatically" true the same
structural way every other recommendation type already does.
"""
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.ai.application.dtos import DraftConversationReplyInput
from modules.ai.application.use_cases._shared import RecommendationBuilder, run_provider
from modules.ai.domain import events as ai_events
from modules.ai.domain.value_objects import ANALYSIS_KIND_CONVERSATION, RECOMMENDATION_TYPE_SUGGESTED_REPLY
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.providers.registry import get_provider
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.communication.infrastructure.models.conversation import Conversation
from modules.communication.infrastructure.repositories.message_repository import MessageRepository

MODULE_NAME = "ai"


class DraftConversationReplyUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, data: DraftConversationReplyInput) -> List[AIRecommendation]:
        conversation = self.db.scalar(
            select(Conversation).where(
                Conversation.id == data.conversation_id, Conversation.company_id == data.company_id
            )
        )
        if conversation is None:
            raise NotFoundError("Conversation not found")

        messages = MessageRepository(self.db).list_for_conversation(
            company_id=data.company_id, conversation_id=conversation.id, limit=100
        )
        material_names = list(self.db.scalars(
            select(StoneMaterial.name).where(StoneMaterial.company_id == data.company_id).limit(500)
        ).all())

        context = {
            "conversation": {
                "customer_id": str(conversation.customer_id) if conversation.customer_id else None,
                "external_contact_name": conversation.external_contact_name,
            },
            "messages": [{"direction": m.direction, "body": m.body, "sender_type": m.sender_type} for m in messages],
            "catalog_material_names": material_names,
        }
        prompt = (
            "Draft a reply to the customer's most recent message in this conversation with a stone/slab "
            "gallery business. Match the language they've been writing in, keep it concise and warm, and "
            "address their question or request directly."
        )

        provider = get_provider(data.provider_name)
        timed = run_provider(
            provider.draft_conversation_reply,
            prompt=prompt,
            context=context,
            db=self.db,
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            analysis_kind=ANALYSIS_KIND_CONVERSATION,
            provider=provider,
        )
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
            provider_call_id=timed.provider_call_id,
        )
        builder.add(
            RECOMMENDATION_TYPE_SUGGESTED_REPLY,
            {"draft_reply": d["draft_reply"], "reply_language": d["reply_language"]},
            d["draft_reply"],
        )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="ai.conversation_reply_drafted",
            entity_type="conversation",
            entity_id=conversation.id,
            diff={"provider": provider.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=ai_events.CONVERSATION_REPLY_DRAFTED,
                company_id=data.company_id,
                payload={"conversation_id": str(conversation.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return builder.created
