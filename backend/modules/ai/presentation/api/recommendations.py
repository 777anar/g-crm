import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.ai.application.dtos import ReviewRecommendationInput
from modules.ai.application.use_cases import ReviewRecommendationUseCase
from modules.ai.domain.exceptions import InvalidReviewDecisionError, RecommendationAlreadyReviewedError
from modules.ai.infrastructure.repositories.recommendation_repository import AIRecommendationRepository
from modules.ai.presentation.schemas.recommendation import (
    AIRecommendationListOut,
    AIRecommendationOut,
    ReviewDecisionRequest,
)

router = APIRouter()


@router.get("/recommendations", response_model=AIRecommendationListOut)
def list_recommendations(
    analysis_kind: Optional[str] = Query(default=None),
    recommendation_type: Optional[str] = Query(default=None),
    related_entity_type: Optional[str] = Query(default=None),
    related_entity_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:read")),
) -> AIRecommendationListOut:
    repo = AIRecommendationRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        analysis_kind=analysis_kind,
        recommendation_type=recommendation_type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        status=status,
        provider=provider,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return AIRecommendationListOut(
        items=[AIRecommendationOut.model_validate(r) for r in page], next_cursor=next_cursor
    )


@router.get("/recommendations/{recommendation_id}", response_model=AIRecommendationOut)
def get_recommendation(
    recommendation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:read")),
) -> AIRecommendationOut:
    recommendation = AIRecommendationRepository(db).get(
        company_id=current_user.active_company_id, recommendation_id=recommendation_id
    )
    if recommendation is None:
        raise NotFoundError("Recommendation not found")
    return AIRecommendationOut.model_validate(recommendation)


@router.post("/recommendations/{recommendation_id}/review", response_model=AIRecommendationOut)
def review_recommendation(
    recommendation_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:write")),
) -> AIRecommendationOut:
    try:
        recommendation = ReviewRecommendationUseCase(db).execute(
            ReviewRecommendationInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                recommendation_id=recommendation_id,
                decision=payload.decision,
                edited_response=payload.edited_response,
            )
        )
    except (RecommendationAlreadyReviewedError, InvalidReviewDecisionError) as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(recommendation)
    return AIRecommendationOut.model_validate(recommendation)
