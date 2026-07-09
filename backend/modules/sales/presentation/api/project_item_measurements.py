import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import CreateProjectItemMeasurementInput, UpdateProjectItemMeasurementInput
from modules.sales.application.use_cases import (
    CreateProjectItemMeasurementUseCase,
    DeleteProjectItemMeasurementUseCase,
    UpdateProjectItemMeasurementUseCase,
)
from modules.sales.infrastructure.repositories.project_item_measurement_repository import (
    ProjectItemMeasurementRepository,
)
from modules.sales.presentation.schemas.project_item_measurement import (
    ProjectItemMeasurementCreate,
    ProjectItemMeasurementListOut,
    ProjectItemMeasurementOut,
    ProjectItemMeasurementUpdate,
)

router = APIRouter()


@router.get("/project-items/{item_id}/measurements", response_model=ProjectItemMeasurementListOut)
def list_measurements(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> ProjectItemMeasurementListOut:
    items = ProjectItemMeasurementRepository(db).list_for_item(
        company_id=current_user.active_company_id, project_item_id=item_id
    )
    return ProjectItemMeasurementListOut(items=[ProjectItemMeasurementOut.model_validate(m) for m in items])


@router.post("/project-items/{item_id}/measurements", response_model=ProjectItemMeasurementOut)
def create_measurement(
    item_id: uuid.UUID,
    payload: ProjectItemMeasurementCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectItemMeasurementOut:
    uc = CreateProjectItemMeasurementUseCase(db)
    measurement = uc.execute(
        CreateProjectItemMeasurementInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            project_item_id=item_id,
            length_mm=payload.length_mm,
            width_mm=payload.width_mm,
            thickness_mm=payload.thickness_mm,
            quantity=payload.quantity,
            measurer_name=payload.measurer_name,
            measured_at=payload.measured_at,
            notes=payload.notes,
            status=payload.status,
        )
    )
    db.commit()
    db.refresh(measurement)
    return ProjectItemMeasurementOut.model_validate(measurement)


@router.patch("/project-item-measurements/{measurement_id}", response_model=ProjectItemMeasurementOut)
def update_measurement(
    measurement_id: uuid.UUID,
    payload: ProjectItemMeasurementUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectItemMeasurementOut:
    uc = UpdateProjectItemMeasurementUseCase(db)
    measurement = uc.execute(
        UpdateProjectItemMeasurementInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            measurement_id=measurement_id,
            length_mm=payload.length_mm,
            width_mm=payload.width_mm,
            thickness_mm=payload.thickness_mm,
            quantity=payload.quantity,
            measurer_name=payload.measurer_name,
            measured_at=payload.measured_at,
            notes=payload.notes,
            status=payload.status,
            customer_signature_document_id=payload.customer_signature_document_id,
        )
    )
    db.commit()
    db.refresh(measurement)
    return ProjectItemMeasurementOut.model_validate(measurement)


@router.delete("/project-item-measurements/{measurement_id}", status_code=204)
def delete_measurement(
    measurement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> None:
    uc = DeleteProjectItemMeasurementUseCase(db)
    uc.execute(
        company_id=current_user.active_company_id,
        actor_user_id=current_user.user_id,
        measurement_id=measurement_id,
    )
    db.commit()
