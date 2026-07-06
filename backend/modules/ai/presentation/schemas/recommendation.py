import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from modules.ai.domain.value_objects import VALID_REVIEW_DECISIONS


class AIRecommendationOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    analysis_kind: str
    recommendation_type: str
    related_entity_type: Optional[str]
    related_entity_id: Optional[uuid.UUID]
    provider: str
    model: str
    prompt: str
    response: Dict[str, Any]
    confidence_score: Optional[float]
    execution_time_ms: Optional[int]
    summary: Optional[str]
    status: str
    edited_response: Optional[Dict[str, Any]]
    requested_by: Optional[uuid.UUID]
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIRecommendationListOut(BaseModel):
    items: List[AIRecommendationOut]
    next_cursor: Optional[str] = None


class ReviewDecisionRequest(BaseModel):
    decision: str
    edited_response: Optional[Dict[str, Any]] = None

    def model_post_init(self, __context) -> None:
        if self.decision not in VALID_REVIEW_DECISIONS:
            raise ValueError(f"decision must be one of {sorted(VALID_REVIEW_DECISIONS)}")
