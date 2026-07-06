"""Aggregates the AI Dashboard from this company's own recent
AIRecommendation history -- bounded Python aggregation over the same
recent-history window `list_for_dashboard` returns, exactly the pragmatic
approach Reports uses for its own dashboards at this dataset scale (no
separate summary/materialized table).
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.ai.application.dtos import GetAIDashboardInput
from modules.ai.domain.value_objects import (
    RECOMMENDATION_STATUS_ACCEPTED,
    RECOMMENDATION_STATUS_PENDING,
    RECOMMENDATION_STATUS_REJECTED,
    RECOMMENDATION_TYPE_DUPLICATE_LEAD,
    RECOMMENDATION_TYPE_FOLLOW_UP,
    RECOMMENDATION_TYPE_LEAD_SCORE,
    RECOMMENDATION_TYPE_MARGIN_RISK,
    RECOMMENDATION_TYPE_MISSING_INFO,
    RECOMMENDATION_TYPE_PRICE_ANOMALY,
    RECOMMENDATION_TYPE_WIN_PROBABILITY,
)
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.repositories.recommendation_repository import AIRecommendationRepository
from modules.crm.domain.value_objects import CUSTOMER_STATUS_COMPLETED, CUSTOMER_STATUS_LOST
from modules.crm.infrastructure.models.customer import Customer

_AT_RISK_TYPES = {RECOMMENDATION_TYPE_MISSING_INFO, RECOMMENDATION_TYPE_DUPLICATE_LEAD, RECOMMENDATION_TYPE_MARGIN_RISK, RECOMMENDATION_TYPE_PRICE_ANOMALY}
_STALLED_AFTER_DAYS = 14
_SCORE_BUCKETS = [(0, 25, "0-25"), (26, 50, "26-50"), (51, 75, "51-75"), (76, 100, "76-100")]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _latest_per_entity(recommendations: List[AIRecommendation], recommendation_type: str) -> Dict[str, AIRecommendation]:
    """recommendations is already ordered newest-first, so the first hit
    per related_entity_id is the current value."""
    latest: Dict[str, AIRecommendation] = {}
    for rec in recommendations:
        if rec.recommendation_type != recommendation_type or not rec.related_entity_id:
            continue
        key = str(rec.related_entity_id)
        if key not in latest:
            latest[key] = rec
    return latest


class GetAIDashboardUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.recommendations = AIRecommendationRepository(db)

    def execute(self, data: GetAIDashboardInput) -> dict:
        recent = self.recommendations.list_for_dashboard(company_id=data.company_id, limit=500)

        # Lead score distribution + sales probability, from the most recent
        # score/probability recommendation per lead (re-analyzing a lead
        # shouldn't double-count it).
        latest_scores = _latest_per_entity(recent, RECOMMENDATION_TYPE_LEAD_SCORE)
        distribution = {label: 0 for _, _, label in _SCORE_BUCKETS}
        for rec in latest_scores.values():
            score = rec.response.get("score", 0)
            for low, high, label in _SCORE_BUCKETS:
                if low <= score <= high:
                    distribution[label] += 1
                    break

        latest_probabilities = _latest_per_entity(recent, RECOMMENDATION_TYPE_WIN_PROBABILITY)
        probabilities = [r.response.get("win_probability", 0) for r in latest_probabilities.values()]
        avg_win_probability = round(sum(probabilities) / len(probabilities), 2) if probabilities else None

        # At-risk customers/leads: anything with a still-pending risk-typed
        # recommendation in the recent window.
        at_risk = [
            {
                "recommendation_id": str(rec.id),
                "related_entity_type": rec.related_entity_type,
                "related_entity_id": str(rec.related_entity_id) if rec.related_entity_id else None,
                "recommendation_type": rec.recommendation_type,
                "summary": rec.summary,
            }
            for rec in recent
            if rec.recommendation_type in _AT_RISK_TYPES and rec.status == RECOMMENDATION_STATUS_PENDING
        ][:20]

        follow_ups = [
            {
                "recommendation_id": str(rec.id),
                "related_entity_type": rec.related_entity_type,
                "related_entity_id": str(rec.related_entity_id) if rec.related_entity_id else None,
                "summary": rec.summary,
                "due_in_days": rec.response.get("due_in_days"),
            }
            for rec in recent
            if rec.recommendation_type == RECOMMENDATION_TYPE_FOLLOW_UP and rec.status == RECOMMENDATION_STATUS_PENDING
        ][:20]

        today = _now().date()
        daily_recommendations = [
            {
                "recommendation_id": str(rec.id),
                "recommendation_type": rec.recommendation_type,
                "summary": rec.summary,
                "created_at": rec.created_at,
            }
            for rec in recent
            if rec.status == RECOMMENDATION_STATUS_PENDING and rec.created_at.date() == today
        ][:50]

        recent_activity = [
            {
                "recommendation_id": str(rec.id),
                "recommendation_type": rec.recommendation_type,
                "analysis_kind": rec.analysis_kind,
                "status": rec.status,
                "provider": rec.provider,
                "summary": rec.summary,
                "created_at": rec.created_at,
                "reviewed_at": rec.reviewed_at,
            }
            for rec in recent[:30]
        ]

        status_counts = {RECOMMENDATION_STATUS_PENDING: 0, RECOMMENDATION_STATUS_ACCEPTED: 0, RECOMMENDATION_STATUS_REJECTED: 0, "edited": 0}
        provider_counts: Dict[str, int] = {}
        execution_times: List[int] = []
        for rec in recent:
            status_counts[rec.status] = status_counts.get(rec.status, 0) + 1
            provider_counts[rec.provider] = provider_counts.get(rec.provider, 0) + 1
            if rec.execution_time_ms is not None:
                execution_times.append(rec.execution_time_ms)
        reviewed_total = status_counts[RECOMMENDATION_STATUS_ACCEPTED] + status_counts[RECOMMENDATION_STATUS_REJECTED]
        acceptance_rate = (
            round(status_counts[RECOMMENDATION_STATUS_ACCEPTED] / reviewed_total, 2) if reviewed_total else None
        )
        usage_stats = {
            "total_recommendations": len(recent),
            "status_counts": status_counts,
            "provider_counts": provider_counts,
            "acceptance_rate": acceptance_rate,
            "avg_execution_time_ms": round(sum(execution_times) / len(execution_times)) if execution_times else None,
        }

        pipeline_health = self._pipeline_health(data.company_id)

        return {
            "lead_score_distribution": distribution,
            "avg_win_probability": avg_win_probability,
            "pipeline_health": pipeline_health,
            "at_risk_customers": at_risk,
            "follow_up_recommendations": follow_ups,
            "daily_recommendations": daily_recommendations,
            "recent_activity": recent_activity,
            "usage_stats": usage_stats,
        }

    def _pipeline_health(self, company_id) -> dict:
        customers = list(self.db.scalars(
            select(Customer).where(Customer.company_id == company_id, Customer.deleted_at.is_(None))
        ).all())
        active = [c for c in customers if c.status not in (CUSTOMER_STATUS_LOST, CUSTOMER_STATUS_COMPLETED)]
        stalled_cutoff = _now() - timedelta(days=_STALLED_AFTER_DAYS)
        stalled = [c for c in active if c.updated_at and c.updated_at.replace(tzinfo=timezone.utc) < stalled_cutoff]
        stalled_pct = round(len(stalled) / len(active) * 100, 1) if active else 0.0
        return {
            "active_pipeline_count": len(active),
            "stalled_count": len(stalled),
            "stalled_pct": stalled_pct,
        }
