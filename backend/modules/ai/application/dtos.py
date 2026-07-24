"""Application-layer input DTOs for the AI Sales Assistant module."""
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class AnalyzeLeadInput(ActorContext):
    lead_id: uuid.UUID
    provider_name: Optional[str] = None


@dataclass
class AnalyzeConversationInput(ActorContext):
    conversation_id: uuid.UUID
    provider_name: Optional[str] = None


@dataclass
class AnalyzeQuoteInput(ActorContext):
    quote_id: uuid.UUID
    provider_name: Optional[str] = None


@dataclass
class SuggestTasksInput(ActorContext):
    provider_name: Optional[str] = None


@dataclass
class ReviewRecommendationInput(ActorContext):
    recommendation_id: uuid.UUID
    decision: str
    edited_response: Optional[dict] = None


@dataclass
class GetAIDashboardInput(ActorContext):
    pass


@dataclass
class GetAIUsageInput(ActorContext):
    limit: int = 25
    offset: int = 0


@dataclass
class DraftConversationReplyInput(ActorContext):
    conversation_id: uuid.UUID
    provider_name: Optional[str] = None


@dataclass
class DraftQuoteLineItemsInput(ActorContext):
    project_id: uuid.UUID
    provider_name: Optional[str] = None
