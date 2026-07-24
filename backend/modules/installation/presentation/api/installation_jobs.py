import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError, ValidationAPIError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.installation.application.dtos import (
    AddInstallationPhotoInput,
    CreateInstallationJobInput,
    RequestJobSignatureInput,
    SimulateJobSignatureInput,
    UpdateInstallationJobInput,
    UpdateInstallationJobStatusInput,
)
from modules.installation.application.use_cases import (
    AddInstallationPhotoUseCase,
    CreateInstallationJobUseCase,
    RequestJobSignatureUseCase,
    SimulateJobSignatureUseCase,
    UpdateInstallationJobStatusUseCase,
    UpdateInstallationJobUseCase,
)
from modules.installation.domain.exceptions import (
    CrewInactiveError,
    InvalidJobTransitionError,
    JobAlreadyExistsError,
    OrderNotReadyForInstallationError,
)
from modules.installation.infrastructure.repositories.installation_job_repository import (
    InstallationJobRepository,
)
from modules.installation.infrastructure.repositories.installation_photo_repository import (
    InstallationPhotoRepository,
)
from modules.installation.presentation.schemas.installation_job import (
    InstallationJobCreate,
    InstallationJobListOut,
    InstallationJobOut,
    InstallationJobStatusUpdate,
    InstallationJobUpdate,
    InstallationPhotoCreate,
    InstallationPhotoListOut,
    InstallationPhotoOut,
    RequestJobSignatureRequest,
    SimulateJobSignatureRequest,
)

router = APIRouter()

_BUSINESS_RULE_ERRORS = (
    OrderNotReadyForInstallationError,
    JobAlreadyExistsError,
    CrewInactiveError,
    InvalidJobTransitionError,
)


@router.get("", response_model=InstallationJobListOut)
def list_installation_jobs(
    status: Optional[str] = Query(default=None),
    crew_id: Optional[uuid.UUID] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=200),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> InstallationJobListOut:
    repo = InstallationJobRepository(db)
    offset = decode_cursor(cursor)
    jobs = repo.list(
        company_id=current_user.active_company_id,
        status=status,
        crew_id=crew_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(jobs) > limit
    page = jobs[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return InstallationJobListOut(items=[InstallationJobOut.model_validate(j) for j in page], next_cursor=next_cursor)


@router.post("", response_model=InstallationJobOut)
def create_installation_job(
    payload: InstallationJobCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> InstallationJobOut:
    uc = CreateInstallationJobUseCase(db)
    try:
        job = uc.execute(
            CreateInstallationJobInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                order_id=payload.order_id,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(job)
    return InstallationJobOut.model_validate(job)


@router.get("/by-order/{order_id}", response_model=InstallationJobOut)
def get_installation_job_for_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> InstallationJobOut:
    job = InstallationJobRepository(db).get_for_order(
        company_id=current_user.active_company_id, order_id=order_id
    )
    if job is None:
        raise NotFoundError("This order has no installation job yet")
    return InstallationJobOut.model_validate(job)


@router.get("/{job_id}", response_model=InstallationJobOut)
def get_installation_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> InstallationJobOut:
    job = InstallationJobRepository(db).get(company_id=current_user.active_company_id, job_id=job_id)
    if job is None:
        raise NotFoundError("Installation job not found")
    return InstallationJobOut.model_validate(job)


@router.patch("/{job_id}", response_model=InstallationJobOut)
def update_installation_job(
    job_id: uuid.UUID,
    payload: InstallationJobUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> InstallationJobOut:
    uc = UpdateInstallationJobUseCase(db)
    try:
        job = uc.execute(
            UpdateInstallationJobInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                job_id=job_id,
                crew_id=payload.crew_id,
                scheduled_date=payload.scheduled_date,
                scheduled_time_slot=payload.scheduled_time_slot,
                route_sequence=payload.route_sequence,
                notes=payload.notes,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(job)
    return InstallationJobOut.model_validate(job)


@router.post("/{job_id}/status", response_model=InstallationJobOut)
def update_installation_job_status(
    job_id: uuid.UUID,
    payload: InstallationJobStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> InstallationJobOut:
    uc = UpdateInstallationJobStatusUseCase(db)
    try:
        job = uc.execute(
            UpdateInstallationJobStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                job_id=job_id,
                status=payload.status,
                cancelled_reason=payload.cancelled_reason,
                completion_notes=payload.completion_notes,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(job)
    return InstallationJobOut.model_validate(job)


@router.get("/{job_id}/photos", response_model=InstallationPhotoListOut)
def list_installation_photos(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> InstallationPhotoListOut:
    photos = InstallationPhotoRepository(db).list_for_job(
        company_id=current_user.active_company_id, installation_job_id=job_id
    )
    return InstallationPhotoListOut(items=[InstallationPhotoOut.model_validate(p) for p in photos])


@router.post("/{job_id}/photos", response_model=InstallationPhotoOut)
def add_installation_photo(
    job_id: uuid.UUID,
    payload: InstallationPhotoCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> InstallationPhotoOut:
    photo = AddInstallationPhotoUseCase(db).execute(
        AddInstallationPhotoInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            job_id=job_id,
            document_id=payload.document_id,
            photo_type=payload.photo_type,
            caption=payload.caption,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    return InstallationPhotoOut.model_validate(photo)


# ── E-signature integration (Phase 22) ──────────────────────────────────────


@router.post("/{job_id}/request-signature", response_model=InstallationJobOut)
def request_job_signature(
    job_id: uuid.UUID,
    payload: RequestJobSignatureRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> InstallationJobOut:
    job = RequestJobSignatureUseCase(db).execute(
        RequestJobSignatureInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            job_id=job_id,
            provider_name=payload.provider,
        )
    )
    db.commit()
    db.refresh(job)
    return InstallationJobOut.model_validate(job)


@router.post("/{job_id}/simulate-signature", response_model=InstallationJobOut)
def simulate_job_signature(
    job_id: uuid.UUID,
    payload: SimulateJobSignatureRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> InstallationJobOut:
    try:
        job = SimulateJobSignatureUseCase(db).execute(
            SimulateJobSignatureInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                job_id=job_id,
                outcome=payload.outcome,
            )
        )
    except ValueError as exc:
        raise ValidationAPIError(str(exc)) from exc
    db.commit()
    db.refresh(job)
    return InstallationJobOut.model_validate(job)
