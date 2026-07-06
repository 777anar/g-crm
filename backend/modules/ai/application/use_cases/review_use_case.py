"""The human-in-the-loop gate every recommendation passes through.

This is the *only* place a recommendation's own status ever changes, and it
never mutates any other module's data: accepting a `task_suggestion`
recommendation does not create a Task, accepting a `conversation_link_
suggestion` does not update the Conversation's `customer_id`, and so on.
"AI never performs business actions automatically" is therefore a structural
property of this use case, not just a UI convention -- a human still has to
open the Task/Conversation/Lead screen and make the change themselves,
informed by the recommendation.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.ai.application.dtos import ReviewRecommendationInput
from modules.ai.domain import events as ai_events
from modules.ai.domain.exceptions import InvalidReviewDecisionError, RecommendationAlreadyReviewedError
from modules.ai.domain.value_objects import (
    REVIEW_DECISION_ACCEPT,
    REVIEW_DECISION_EDIT,
    REVIEW_DECISION_REJECT,
    TERMINAL_RECOMMENDATION_STATUSES,
    VALID_REVIEW_DECISIONS,
    status_for_decision,
)
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.repositories.recommendation_repository import AIRecommendationRepository

MODULE_NAME = "ai"

_EVENT_FOR_DECISION = {
    REVIEW_DECISION_ACCEPT: ai_events.RECOMMENDATION_ACCEPTED,
    REVIEW_DECISION_REJECT: ai_events.RECOMMENDATION_REJECTED,
    REVIEW_DECISION_EDIT: ai_events.RECOMMENDATION_EDITED,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewRecommendationUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.recommendations = AIRecommendationRepository(db)

    def execute(self, data: ReviewRecommendationInput) -> AIRecommendation:
        if data.decision not in VALID_REVIEW_DECISIONS:
            raise InvalidReviewDecisionError(f"Invalid review decision '{data.decision}'")

        recommendation = self.recommendations.get(
            company_id=data.company_id, recommendation_id=data.recommendation_id
        )
        if recommendation is None:
            raise NotFoundError("Recommendation not found")
        if recommendation.status in TERMINAL_RECOMMENDATION_STATUSES:
            raise RecommendationAlreadyReviewedError(
                f"This recommendation was already {recommendation.status}"
            )

        old_status = recommendation.status
        recommendation.status = status_for_decision(data.decision)
        recommendation.reviewed_by = data.actor_user_id
        recommendation.reviewed_at = _now()
        if data.decision == REVIEW_DECISION_EDIT:
            recommendation.edited_response = data.edited_response

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="ai.recommendation_reviewed",
            entity_type="ai_recommendation",
            entity_id=recommendation.id,
            diff={"status": {"old": old_status, "new": recommendation.status}, "decision": data.decision},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=_EVENT_FOR_DECISION[data.decision],
                company_id=data.company_id,
                payload={"recommendation_id": str(recommendation.id), "recommendation_type": recommendation.recommendation_type},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return recommendation
