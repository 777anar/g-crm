import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.customer_portal.application.dtos import (
    EnablePortalAccessInput,
    ResetPortalPasswordInput,
    SetPortalAccessActiveInput,
)
from modules.customer_portal.application.use_cases import (
    EnablePortalAccessUseCase,
    ResetPortalPasswordUseCase,
    SetPortalAccessActiveUseCase,
)
from modules.customer_portal.infrastructure.repositories.customer_login_repository import CustomerLoginRepository
from modules.customer_portal.presentation.schemas.portal import (
    EnablePortalAccessRequest,
    PortalAccessOut,
    ResetPortalPasswordRequest,
    SetPortalAccessActiveRequest,
)

router = APIRouter()


@router.get("/admin/customers/{customer_id}/access", response_model=PortalAccessOut)
def get_portal_access(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("customer_portal:access:read")),
) -> PortalAccessOut:
    login = CustomerLoginRepository(db).get_by_customer(
        company_id=current_user.active_company_id, customer_id=customer_id
    )
    if login is None:
        raise NotFoundError("Portal access is not enabled for this customer")
    return PortalAccessOut.model_validate(login)


@router.post("/admin/customers/{customer_id}/access", response_model=PortalAccessOut)
def enable_portal_access(
    customer_id: uuid.UUID,
    payload: EnablePortalAccessRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("customer_portal:access:write")),
) -> PortalAccessOut:
    login = EnablePortalAccessUseCase(db).execute(
        EnablePortalAccessInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            customer_id=customer_id,
            email=payload.email,
            password=payload.password,
        )
    )
    db.commit()
    db.refresh(login)
    return PortalAccessOut.model_validate(login)


@router.post("/admin/customers/{customer_id}/access/reset-password", response_model=PortalAccessOut)
def reset_portal_password(
    customer_id: uuid.UUID,
    payload: ResetPortalPasswordRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("customer_portal:access:write")),
) -> PortalAccessOut:
    login = ResetPortalPasswordUseCase(db).execute(
        ResetPortalPasswordInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            customer_id=customer_id,
            password=payload.password,
        )
    )
    db.commit()
    db.refresh(login)
    return PortalAccessOut.model_validate(login)


@router.post("/admin/customers/{customer_id}/access/status", response_model=PortalAccessOut)
def set_portal_access_active(
    customer_id: uuid.UUID,
    payload: SetPortalAccessActiveRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("customer_portal:access:write")),
) -> PortalAccessOut:
    login = SetPortalAccessActiveUseCase(db).execute(
        SetPortalAccessActiveInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            customer_id=customer_id,
            is_active=payload.is_active,
        )
    )
    db.commit()
    db.refresh(login)
    return PortalAccessOut.model_validate(login)
