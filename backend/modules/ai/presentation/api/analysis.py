import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.ai.application.dtos import (
    AnalyzeConversationInput,
    AnalyzeLeadInput,
    AnalyzeQuoteInput,
    SuggestTasksInput,
)
from modules.ai.application.use_cases import (
    AnalyzeConversationUseCase,
    AnalyzeLeadUseCase,
    AnalyzeQuoteUseCase,
    SuggestTasksUseCase,
)
from modules.ai.presentation.schemas.analysis import AnalyzeRequest
from modules.ai.presentation.schemas.recommendation import AIRecommendationListOut, AIRecommendationOut

router = APIRouter()


@router.post("/leads/{lead_id}/analyze", response_model=AIRecommendationListOut)
def analyze_lead(
    lead_id: uuid.UUID,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:write")),
) -> AIRecommendationListOut:
    created = AnalyzeLeadUseCase(db).execute(
        AnalyzeLeadInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            lead_id=lead_id,
            provider_name=payload.provider,
        )
    )
    db.commit()
    for rec in created:
        db.refresh(rec)
    return AIRecommendationListOut(items=[AIRecommendationOut.model_validate(r) for r in created])


@router.post("/conversations/{conversation_id}/analyze", response_model=AIRecommendationListOut)
def analyze_conversation(
    conversation_id: uuid.UUID,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:write")),
) -> AIRecommendationListOut:
    created = AnalyzeConversationUseCase(db).execute(
        AnalyzeConversationInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            conversation_id=conversation_id,
            provider_name=payload.provider,
        )
    )
    db.commit()
    for rec in created:
        db.refresh(rec)
    return AIRecommendationListOut(items=[AIRecommendationOut.model_validate(r) for r in created])


@router.post("/quotes/{quote_id}/analyze", response_model=AIRecommendationListOut)
def analyze_quote(
    quote_id: uuid.UUID,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:write")),
) -> AIRecommendationListOut:
    created = AnalyzeQuoteUseCase(db).execute(
        AnalyzeQuoteInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            quote_id=quote_id,
            provider_name=payload.provider,
        )
    )
    db.commit()
    for rec in created:
        db.refresh(rec)
    return AIRecommendationListOut(items=[AIRecommendationOut.model_validate(r) for r in created])


@router.post("/tasks/suggest", response_model=AIRecommendationListOut)
def suggest_tasks(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:write")),
) -> AIRecommendationListOut:
    created = SuggestTasksUseCase(db).execute(
        SuggestTasksInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            provider_name=payload.provider,
        )
    )
    db.commit()
    for rec in created:
        db.refresh(rec)
    return AIRecommendationListOut(items=[AIRecommendationOut.model_validate(r) for r in created])
