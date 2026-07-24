import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from core.api.errors import ValidationAPIError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import (
    CreateProjectItemMeasurementInput,
    HandleMeasurementSignatureWebhookInput,
    RequestMeasurementSignatureInput,
    SimulateMeasurementSignatureInput,
    UpdateProjectItemMeasurementInput,
)
from modules.sales.application.use_cases import (
    CreateProjectItemMeasurementUseCase,
    DeleteProjectItemMeasurementUseCase,
    HandleMeasurementSignatureWebhookUseCase,
    RequestMeasurementSignatureUseCase,
    SimulateMeasurementSignatureUseCase,
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
    RequestSignatureRequest,
    SimulateSignatureRequest,
)

router = APIRouter()


@router.get("/measurements", response_model=ProjectItemMeasurementListOut)
def list_measurements_for_company(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> ProjectItemMeasurementListOut:
    items = ProjectItemMeasurementRepository(db).list_for_company(
        company_id=current_user.active_company_id, date_from=date_from, date_to=date_to
    )
    return ProjectItemMeasurementListOut(items=[ProjectItemMeasurementOut.model_validate(m) for m in items])


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


# ── E-signature integration (Phase 22) ──────────────────────────────────────


@router.post("/project-item-measurements/{measurement_id}/request-signature", response_model=ProjectItemMeasurementOut)
def request_measurement_signature(
    measurement_id: uuid.UUID,
    payload: RequestSignatureRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectItemMeasurementOut:
    measurement = RequestMeasurementSignatureUseCase(db).execute(
        RequestMeasurementSignatureInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            measurement_id=measurement_id,
            provider_name=payload.provider,
        )
    )
    db.commit()
    db.refresh(measurement)
    return ProjectItemMeasurementOut.model_validate(measurement)


@router.post("/project-item-measurements/{measurement_id}/simulate-signature", response_model=ProjectItemMeasurementOut)
def simulate_measurement_signature(
    measurement_id: uuid.UUID,
    payload: SimulateSignatureRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectItemMeasurementOut:
    try:
        measurement = SimulateMeasurementSignatureUseCase(db).execute(
            SimulateMeasurementSignatureInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                measurement_id=measurement_id,
                outcome=payload.outcome,
            )
        )
    except ValueError as exc:
        raise ValidationAPIError(str(exc)) from exc
    db.commit()
    db.refresh(measurement)
    return ProjectItemMeasurementOut.model_validate(measurement)


@router.post("/webhooks/esignature/{provider}")
def receive_measurement_signature_webhook(
    provider: str,
    json_payload: str = Form(..., alias="json"),
    db: Session = Depends(get_db),
) -> dict:
    """Public -- deliberately NOT wired through require_permission, since
    external e-signature providers never carry our JWTs. Trust comes
    entirely from the provider's own signature scheme, verified inside
    `HandleMeasurementSignatureWebhookUseCase`. Mirrors Communication's
    identical `webhooks.py` convention."""
    HandleMeasurementSignatureWebhookUseCase(db).execute(
        HandleMeasurementSignatureWebhookInput(payload=json_payload, provider_name=provider)
    )
    db.commit()
    return {"received": True}
