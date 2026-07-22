import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.production.application.dtos import CreateProductionStageInput, UpdateProductionStageInput
from modules.production.application.use_cases.production_stage_use_cases import (
    CreateProductionStageUseCase,
    UpdateProductionStageUseCase,
)
from modules.production.infrastructure.repositories.production_stage_repository import ProductionStageRepository
from modules.production.presentation.schemas.work_order import (
    ProductionStageCreate,
    ProductionStageListOut,
    ProductionStageOut,
    ProductionStageUpdate,
)

router = APIRouter()


@router.get("/stages", response_model=ProductionStageListOut)
def list_production_stages(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:read")),
) -> ProductionStageListOut:
    stages = ProductionStageRepository(db).list_or_seed_defaults(company_id=current_user.active_company_id)
    db.commit()
    return ProductionStageListOut(items=[ProductionStageOut.model_validate(s) for s in stages])


@router.post("/stages", response_model=ProductionStageOut)
def create_production_stage(
    payload: ProductionStageCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:write")),
) -> ProductionStageOut:
    stage = CreateProductionStageUseCase(db).execute(
        CreateProductionStageInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(stage)
    return ProductionStageOut.model_validate(stage)


@router.patch("/stages/{stage_id}", response_model=ProductionStageOut)
def update_production_stage(
    stage_id: uuid.UUID,
    payload: ProductionStageUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:write")),
) -> ProductionStageOut:
    stage = UpdateProductionStageUseCase(db).execute(
        UpdateProductionStageInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            stage_id=stage_id,
            name=payload.name,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
    )
    db.commit()
    db.refresh(stage)
    return ProductionStageOut.model_validate(stage)
