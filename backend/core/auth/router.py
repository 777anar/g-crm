from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.auth import service
from core.auth.schemas import (
    CompanyMembership,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    SelectCompanyRequest,
    TokenResponse,
)
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, get_current_user
from core.rbac.rate_limit import login_rate_limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    client_ip = request.client.host if request.client else "unknown"
    login_rate_limiter.check(client_ip)
    user = service.authenticate_user(db, email=payload.email, password=payload.password)
    access_token, refresh_token, memberships = service.issue_login_tokens(db, user=user)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        companies=[CompanyMembership(id=company.id, name=company.name, role=role) for role, company in memberships],
    )


@router.post("/select-company", response_model=TokenResponse)
def select_company(
    payload: SelectCompanyRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TokenResponse:
    access_token = service.select_company(db, user_id=current_user.user_id, company_id=payload.company_id)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    access_token = service.refresh_access_token(db, refresh_token=payload.refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
def logout(payload: RefreshRequest) -> dict:
    # Revokes every refresh token issued to this user before now (see
    # core/auth/token_denylist.py) -- logout-everywhere, not just a
    # client-side token discard. The access token already in the client's
    # hands keeps working until its own short (15-minute default) expiry.
    service.logout_everywhere(refresh_token=payload.refresh_token)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
def me(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> MeResponse:
    user = service.get_user_or_404(db, current_user.user_id)
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        active_company_id=current_user.active_company_id,
        role=current_user.role,
        module_permissions=current_user.module_permissions,
    )
