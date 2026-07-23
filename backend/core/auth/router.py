from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from core.api.errors import UnauthenticatedError
from core.auth import service
from core.auth.schemas import (
    CompanyMembership,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MfaCodeRequest,
    MfaSetupOut,
    MfaVerifyRequest,
    RefreshRequest,
    SelectCompanyRequest,
    TokenResponse,
)
from core.auth.security import ACCESS_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME, decode_token
from core.config import settings
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, get_current_user
from core.rbac.rate_limit import login_rate_limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Refresh cookie is scoped to /api/v1/auth so it's never sent to ordinary
# module endpoints (only login/select-company/refresh/logout/mfa live under
# this prefix) -- the access cookie needs the wider "/" scope since every
# route under the API needs it.
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_access_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        path=_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)


def _claims_from_access_token(access_token: str) -> dict:
    payload = decode_token(access_token)
    company_id = payload.get("active_company_id")
    return {
        "active_company_id": company_id,
        "role": payload.get("role"),
        "module_permissions": payload.get("module_permissions") or {},
    }


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    client_ip = request.client.host if request.client else "unknown"
    login_rate_limiter.check(client_ip)
    user = service.authenticate_user(db, email=payload.email, password=payload.password)

    if user.mfa_enabled:
        mfa_token = service.begin_mfa_challenge(user=user)
        return LoginResponse(mfa_required=True, mfa_token=mfa_token, companies=[])

    access_token, refresh_token, memberships = service.issue_login_tokens(db, user=user)
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        companies=[CompanyMembership(id=company.id, name=company.name, role=role) for role, company in memberships],
    )


@router.post("/mfa/verify", response_model=LoginResponse)
def verify_mfa(payload: MfaVerifyRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    user = service.verify_mfa_challenge(db, mfa_token=payload.mfa_token, code=payload.code)
    access_token, refresh_token, memberships = service.issue_login_tokens(db, user=user)
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        companies=[CompanyMembership(id=company.id, name=company.name, role=role) for role, company in memberships],
    )


@router.post("/mfa/setup", response_model=MfaSetupOut)
def setup_mfa(
    response: Response,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> MfaSetupOut:
    user = service.get_user_or_404(db, current_user.user_id)
    secret, uri = service.setup_mfa(user=user)
    db.commit()
    return MfaSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/mfa/enable")
def enable_mfa(
    payload: MfaCodeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    user = service.get_user_or_404(db, current_user.user_id)
    service.enable_mfa(user=user, code=payload.code)
    db.commit()
    return {"status": "ok", "mfa_enabled": True}


@router.post("/mfa/disable")
def disable_mfa(
    payload: MfaCodeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    user = service.get_user_or_404(db, current_user.user_id)
    service.disable_mfa(user=user, code=payload.code)
    db.commit()
    return {"status": "ok", "mfa_enabled": False}


@router.post("/select-company", response_model=TokenResponse)
def select_company(
    payload: SelectCompanyRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TokenResponse:
    access_token = service.select_company(db, user_id=current_user.user_id, company_id=payload.company_id)
    _set_access_cookie(response, access_token)
    return TokenResponse(access_token=access_token, **_claims_from_access_token(access_token))


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = None,
    db: Session = Depends(get_db),
) -> TokenResponse:
    refresh_token = (payload.refresh_token if payload else None) or request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise UnauthenticatedError("Missing refresh token")
    access_token = service.refresh_access_token(db, refresh_token=refresh_token)
    _set_access_cookie(response, access_token)
    return TokenResponse(access_token=access_token, **_claims_from_access_token(access_token))


@router.post("/logout")
def logout(request: Request, response: Response, payload: Optional[RefreshRequest] = None) -> dict:
    # Revokes every refresh token issued to this user before now (see
    # core/auth/token_denylist.py) -- logout-everywhere, not just a
    # client-side token discard. The access token already in the client's
    # hands keeps working until its own short (15-minute default) expiry.
    refresh_token = (payload.refresh_token if payload else None) or request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token:
        service.logout_everywhere(refresh_token=refresh_token)
    _clear_auth_cookies(response)
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
        mfa_enabled=user.mfa_enabled,
    )
