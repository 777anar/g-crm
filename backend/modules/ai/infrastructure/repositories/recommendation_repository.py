import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.ai.infrastructure.models.recommendation import AIRecommendation

_SORTABLE_COLUMNS = {
    "created_at": AIRecommendation.created_at,
    "updated_at": AIRecommendation.updated_at,
    "status": AIRecommendation.status,
}
DEFAULT_SORT = "-created_at"


class AIRecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, recommendation: AIRecommendation) -> AIRecommendation:
        self.db.add(recommendation)
        self.db.flush()
        return recommendation

    def get(self, *, company_id: uuid.UUID, recommendation_id: uuid.UUID) -> Optional[AIRecommendation]:
        return self.db.scalar(
            select(AIRecommendation).where(
                AIRecommendation.id == recommendation_id, AIRecommendation.company_id == company_id
            )
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        analysis_kind: Optional[str] = None,
        recommendation_type: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        provider: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[AIRecommendation]:
        stmt = select(AIRecommendation).where(AIRecommendation.company_id == company_id)
        if analysis_kind:
            stmt = stmt.where(AIRecommendation.analysis_kind == analysis_kind)
        if recommendation_type:
            stmt = stmt.where(AIRecommendation.recommendation_type == recommendation_type)
        if related_entity_type:
            stmt = stmt.where(AIRecommendation.related_entity_type == related_entity_type)
        if related_entity_id:
            stmt = stmt.where(AIRecommendation.related_entity_id == related_entity_id)
        if status:
            stmt = stmt.where(AIRecommendation.status == status)
        if provider:
            stmt = stmt.where(AIRecommendation.provider == provider)

        sort = sort or DEFAULT_SORT
        descending = sort.startswith("-")
        column = _SORTABLE_COLUMNS.get(sort.lstrip("-"), AIRecommendation.created_at)
        stmt = stmt.order_by(column.desc() if descending else column.asc())

        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_for_dashboard(self, *, company_id: uuid.UUID, limit: int = 500) -> List[AIRecommendation]:
        """A bounded recent-history window the dashboard aggregates over in
        Python -- same pragmatic approach Reports uses for its own
        aggregations, appropriate at this dataset scale rather than
        maintaining separate summary tables."""
        stmt = (
            select(AIRecommendation)
            .where(AIRecommendation.company_id == company_id)
            .order_by(AIRecommendation.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
