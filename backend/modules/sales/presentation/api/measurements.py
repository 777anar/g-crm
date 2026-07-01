import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import CreateMeasurementInput, UpdateMeasurementInput
from modules.sales.application.use_cases import (
    CreateMeasurementUseCase,
    DeleteMeasurementUseCase,
    UpdateMeasurementUseCase,
)
from modules.sales.infrastructure.repositories.measurement_repository import MeasurementRepository
from modules.sales.presentation.schemas.measurement import (
    MeasurementCreate,
    MeasurementListOut,
    MeasurementOut,
    MeasurementUpdate,
)

router = APIRouter()


@router.get("/sections/{section_id}/measurements", response_model=MeasurementListOut)
def list_measurements(
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:read")),
) -> MeasurementListOut:
    items = MeasurementRepository(db).list_for_section(
        company_id=current_user.active_company_id, section_id=section_id
    )
    return MeasurementListOut(items=[MeasurementOut.model_validate(m) for m in items])


@router.post("/sections/{section_id}/measurements", response_model=MeasurementOut)
def create_measurement(
    section_id: uuid.UUID,
    payload: MeasurementCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> MeasurementOut:
    uc = CreateMeasurementUseCase(db)
    measurement = uc.execute(
        CreateMeasurementInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            section_id=section_id,
            label=payload.label,
            length_mm=payload.length_mm,
            width_mm=payload.width_mm,
            thickness_mm=payload.thickness_mm,
            quantity=payload.quantity,
            waste_pct=payload.waste_pct,
            override_required_area=payload.override_required_area,
            required_area_m2=payload.required_area_m2,
            notes=payload.notes,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(measurement)
    return MeasurementOut.model_validate(measurement)


@router.patch("/measurements/{measurement_id}", response_model=MeasurementOut)
def update_measurement(
    measurement_id: uuid.UUID,
    payload: MeasurementUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> MeasurementOut:
    uc = UpdateMeasurementUseCase(db)
    measurement = uc.execute(
        UpdateMeasurementInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            measurement_id=measurement_id,
            label=payload.label,
            length_mm=payload.length_mm,
            width_mm=payload.width_mm,
            thickness_mm=payload.thickness_mm,
            quantity=payload.quantity,
            waste_pct=payload.waste_pct,
            override_required_area=payload.override_required_area,
            required_area_m2=payload.required_area_m2,
            notes=payload.notes,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(measurement)
    return MeasurementOut.model_validate(measurement)


@router.delete("/measurements/{measurement_id}", status_code=204)
def delete_measurement(
    measurement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> None:
    uc = DeleteMeasurementUseCase(db)
    uc.execute(
        company_id=current_user.active_company_id,
        actor_user_id=current_user.user_id,
        measurement_id=measurement_id,
    )
    db.commit()
