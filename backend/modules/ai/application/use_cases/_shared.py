"""Shared helpers for the four analysis use cases -- factored out so each
one only has to describe *what* context it builds and which recommendation
types it produces, not repeat the provider-timing/persistence boilerplate.

Phase 21 additions: every provider call (mock or real) is rate-limited and
budget-checked per company before it runs, and logged to `AIProviderCallLog`
whether it succeeds or fails -- the audit trail "every AI-generated
recommendation should be traceable to the exact prompt and model response
that produced it" needs, plus the data `AIBudgetExceededError` reads back to
enforce the daily spend cap.
"""
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from core.config import settings
from modules.ai.domain.exceptions import AIBudgetExceededError, AIRateLimitedError
from modules.ai.infrastructure.models.provider_call_log import AIProviderCallLog
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.providers.base import AIAnalysisResult, AIProvider
from modules.ai.infrastructure.rate_limit import ai_analysis_rate_limiter
from modules.ai.infrastructure.repositories.provider_call_log_repository import AIProviderCallLogRepository
from modules.ai.infrastructure.repositories.recommendation_repository import AIRecommendationRepository


@dataclass
class TimedAnalysis:
    result: AIAnalysisResult
    execution_time_ms: int
    provider_call_id: uuid.UUID


def _check_usage_allowed(db: Session, *, company_id: uuid.UUID) -> None:
    """Rate limit (in-process, per company) then daily spend budget (real
    cost accumulated in `ai_provider_call_logs`, read fresh every call --
    correct at whatever traffic this single-instance deployment sees today;
    a future multi-instance deployment would need this counter in Redis too,
    same caveat `FixedWindowRateLimiter` already documents for itself)."""
    try:
        ai_analysis_rate_limiter.check(str(company_id))
    except Exception as exc:  # core.api.errors.RateLimitedError -- re-raised as our own domain error
        raise AIRateLimitedError(str(exc)) from exc

    if settings.ai_daily_budget_usd <= 0:
        return
    today_start = datetime.combine(datetime.now(timezone.utc).date(), dt_time.min, tzinfo=timezone.utc)
    spent_today = AIProviderCallLogRepository(db).total_cost_since(company_id=company_id, since=today_start)
    if spent_today >= Decimal(str(settings.ai_daily_budget_usd)):
        raise AIBudgetExceededError(
            f"This company has reached its daily AI spend cap (${settings.ai_daily_budget_usd:.2f}); "
            "it resets at midnight UTC. Contact an administrator to raise the cap in the meantime."
        )


def run_provider(
    fn: Callable[..., AIAnalysisResult],
    *,
    prompt: str,
    context: dict,
    db: Session,
    company_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    analysis_kind: str,
    provider: AIProvider,
) -> TimedAnalysis:
    log_repo = AIProviderCallLogRepository(db)
    started = time.perf_counter()
    try:
        _check_usage_allowed(db, company_id=company_id)
        result = fn(prompt=prompt, context=context)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        log_repo.add(AIProviderCallLog(
            company_id=company_id,
            requested_by=actor_user_id,
            analysis_kind=analysis_kind,
            provider=provider.name,
            model=provider.model,
            prompt=prompt,
            latency_ms=latency_ms,
            success=False,
            error_message=str(exc)[:2000],
        ))
        # Committed here, not left for the caller's own db.commit(): the use
        # case is about to propagate this exception (no recommendations were
        # created), and the request's session closes on an uncommitted
        # rollback on the way out -- without an explicit commit, the one
        # part of this call that IS worth keeping (the failure itself, for
        # cost/ops visibility and the budget check above reading it back)
        # would silently vanish along with everything else.
        db.commit()
        raise

    execution_time_ms = int((time.perf_counter() - started) * 1000)
    log = log_repo.add(AIProviderCallLog(
        company_id=company_id,
        requested_by=actor_user_id,
        analysis_kind=analysis_kind,
        provider=provider.name,
        model=provider.model,
        prompt=prompt,
        raw_response=result.raw_response,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
        latency_ms=execution_time_ms,
        success=True,
    ))
    db.flush()
    return TimedAnalysis(result=result, execution_time_ms=execution_time_ms, provider_call_id=log.id)


class RecommendationBuilder:
    """Collects the recommendations one analysis call produces, all sharing
    the same prompt/provider/model/confidence/execution_time/requested_by
    and the same `provider_call_id` (Phase 21) tracing them back to the
    exact provider call that produced them."""

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
        provider_call_id: Optional[uuid.UUID] = None,
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
        self._provider_call_id = provider_call_id
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
            provider_call_id=self._provider_call_id,
        )
        self.repo.add(rec)
        self.created.append(rec)
        return rec
