"""Shared helpers for the four analysis use cases -- factored out so each
one only has to describe *what* context it builds and which recommendation
types it produces, not repeat the provider-timing/persistence boilerplate.
"""
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.providers.base import AIAnalysisResult, AIProvider
from modules.ai.infrastructure.repositories.recommendation_repository import AIRecommendationRepository


@dataclass
class TimedAnalysis:
    result: AIAnalysisResult
    execution_time_ms: int


def run_provider(fn: Callable[..., AIAnalysisResult], *, prompt: str, context: dict) -> TimedAnalysis:
    started = time.perf_counter()
    result = fn(prompt=prompt, context=context)
    return TimedAnalysis(result=result, execution_time_ms=int((time.perf_counter() - started) * 1000))


class RecommendationBuilder:
    """Collects the recommendations one analysis call produces, all sharing
    the same prompt/provider/model/confidence/execution_time/requested_by."""

    def __init__(
        self,
        db: Session,
        *,
        company_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        analysis_kind: str,
        related_entity_type: Optional[str],
        related_entity_id: Optional[uuid.UUID],
        provider: AIProvider,
        prompt: str,
        confidence: float,
        execution_time_ms: int,
    ):
        self.repo = AIRecommendationRepository(db)
        self._company_id = company_id
        self._actor_user_id = actor_user_id
        self._analysis_kind = analysis_kind
        self._related_entity_type = related_entity_type
        self._related_entity_id = related_entity_id
        self._provider = provider
        self._prompt = prompt
        self._confidence = Decimal(str(round(confidence, 3)))
        self._execution_time_ms = execution_time_ms
        self.created: List[AIRecommendation] = []

    def add(
        self,
        recommendation_type: str,
        response: Dict[str, Any],
        summary: str,
        *,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[uuid.UUID] = None,
    ) -> AIRecommendation:
        rec = AIRecommendation(
            company_id=self._company_id,
            analysis_kind=self._analysis_kind,
            recommendation_type=recommendation_type,
            related_entity_type=related_entity_type or self._related_entity_type,
            related_entity_id=related_entity_id or self._related_entity_id,
            provider=self._provider.name,
            model=self._provider.model,
            prompt=self._prompt,
            response=response,
            confidence_score=self._confidence,
            execution_time_ms=self._execution_time_ms,
            summary=(summary or "")[:500] or None,
            requested_by=self._actor_user_id,
        )
        self.repo.add(rec)
        self.created.append(rec)
        return rec
