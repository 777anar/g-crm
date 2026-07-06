from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.ai.application.dtos import GetAIDashboardInput
from modules.ai.application.use_cases import GetAIDashboardUseCase
from modules.ai.presentation.schemas.dashboard import AIDashboardOut

router = APIRouter()


@router.get("/dashboard", response_model=AIDashboardOut)
def get_ai_dashboard(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:dashboard:read")),
) -> AIDashboardOut:
    data = GetAIDashboardUseCase(db).execute(
        GetAIDashboardInput(company_id=current_user.active_company_id, actor_user_id=current_user.user_id)
    )
    return AIDashboardOut(**data)
