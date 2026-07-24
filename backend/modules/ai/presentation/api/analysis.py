import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.api.errors import RateLimitedError, ServiceUnavailableError, ValidationAPIError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.ai.application.dtos import (
    AnalyzeConversationInput,
    AnalyzeLeadInput,
    AnalyzeQuoteInput,
    DraftConversationReplyInput,
    DraftQuoteLineItemsInput,
    SuggestTasksInput,
)
from modules.ai.application.use_cases import (
    AnalyzeConversationUseCase,
    AnalyzeLeadUseCase,
    AnalyzeQuoteUseCase,
    DraftConversationReplyUseCase,
    DraftQuoteLineItemsUseCase,
    SuggestTasksUseCase,
)
from modules.ai.domain.exceptions import (
    AIBudgetExceededError,
    AIProviderNotConfiguredError,
    AIProviderUpstreamError,
    AIRateLimitedError,
    UnknownAIProviderError,
)
from modules.ai.presentation.schemas.analysis import AnalyzeRequest
from modules.ai.presentation.schemas.recommendation import AIRecommendationListOut, AIRecommendationOut

router = APIRouter()

# Ordered most-specific-first; a provider/cost-control failure is a real,
# expected outcome now that a real provider exists (Phase 21) -- previously
# only UnknownAIProviderError could occur here and nothing translated it, so
# a bad provider name fell through to a generic 500. All four analysis
# endpoints share this mapping rather than each re-deriving it.
_ERROR_MAP = (
    (UnknownAIProviderError, ValidationAPIError),
    (AIRateLimitedError, RateLimitedError),
    (AIBudgetExceededError, RateLimitedError),
    (AIProviderNotConfiguredError, ServiceUnavailableError),
    (AIProviderUpstreamError, ServiceUnavailableError),
)


def _run(fn):
    try:
        return fn()
    except Exception as exc:
        for domain_exc_type, api_exc_type in _ERROR_MAP:
            if isinstance(exc, domain_exc_type):
                raise api_exc_type(str(exc)) from exc
        raise


@router.post("/leads/{lead_id}/analyze", response_model=AIRecommendationListOut)
def analyze_lead(
    lead_id: uuid.UUID,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:write")),
) -> AIRecommendationListOut:
    created = _run(lambda: AnalyzeLeadUseCase(db).execute(
        AnalyzeLeadInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            lead_id=lead_id,
            provider_name=payload.provider,
        )
    ))
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
    created = _run(lambda: AnalyzeConversationUseCase(db).execute(
        AnalyzeConversationInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            conversation_id=conversation_id,
            provider_name=payload.provider,
        )
    ))
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
    created = _run(lambda: AnalyzeQuoteUseCase(db).execute(
        AnalyzeQuoteInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            quote_id=quote_id,
            provider_name=payload.provider,
        )
    ))
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
    created = _run(lambda: SuggestTasksUseCase(db).execute(
        SuggestTasksInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            provider_name=payload.provider,
        )
    ))
    db.commit()
    for rec in created:
        db.refresh(rec)
    return AIRecommendationListOut(items=[AIRecommendationOut.model_validate(r) for r in created])


# ── AI draft generation (Phase 21 follow-through) ─────────────────────────────


@router.post("/conversations/{conversation_id}/draft-reply", response_model=AIRecommendationListOut)
def draft_conversation_reply(
    conversation_id: uuid.UUID,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:write")),
) -> AIRecommendationListOut:
    """Drafts a reply for a human to review, edit, and send themselves --
    never sent automatically. See `DraftConversationReplyUseCase`."""
    created = _run(lambda: DraftConversationReplyUseCase(db).execute(
        DraftConversationReplyInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            conversation_id=conversation_id,
            provider_name=payload.provider,
        )
    ))
    db.commit()
    for rec in created:
        db.refresh(rec)
    return AIRecommendationListOut(items=[AIRecommendationOut.model_validate(r) for r in created])


@router.post("/projects/{project_id}/draft-quote-items", response_model=AIRecommendationListOut)
def draft_quote_line_items(
    project_id: uuid.UUID,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:recommendations:write")),
) -> AIRecommendationListOut:
    """Drafts suggested Quote line items from a Project's Rooms/Items for a
    human to use when building the actual Quote -- never creates a Quote or
    QuoteSectionItem itself. See `DraftQuoteLineItemsUseCase`."""
    created = _run(lambda: DraftQuoteLineItemsUseCase(db).execute(
        DraftQuoteLineItemsInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            project_id=project_id,
            provider_name=payload.provider,
        )
    ))
    db.commit()
    for rec in created:
        db.refresh(rec)
    return AIRecommendationListOut(items=[AIRecommendationOut.model_validate(r) for r in created])
