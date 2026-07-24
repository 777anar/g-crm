from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.ai.application.dtos import GetAIUsageInput
from modules.ai.application.use_cases import GetAIUsageUseCase
from modules.ai.presentation.schemas.usage import AIUsageOut

router = APIRouter()


@router.get("/usage", response_model=AIUsageOut)
def get_ai_usage(
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:dashboard:read")),
) -> AIUsageOut:
    """Phase 21 cost-control visibility: today's spend/call count against
    this company's configured daily budget, plus a recent provider-call log
    page -- pairs with the enforcement in `_shared.py`'s
    `_check_usage_allowed` so a 429 is explainable, not just experienced."""
    data = GetAIUsageUseCase(db).execute(
        GetAIUsageInput(
            company_id=current_user.active_company_id, actor_user_id=current_user.user_id, limit=limit, offset=offset
        )
    )
    return AIUsageOut(**data)
