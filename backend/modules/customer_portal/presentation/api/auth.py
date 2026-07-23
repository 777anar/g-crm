from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from core.api.errors import UnauthenticatedError
from core.config import settings
from core.db.session import get_db
from core.rbac.rate_limit import FixedWindowRateLimiter
from modules.customer_portal.application import auth_service
from modules.customer_portal.infrastructure.security import (
    CUSTOMER_ACCESS_TOKEN_COOKIE_NAME,
    CUSTOMER_REFRESH_TOKEN_COOKIE_NAME,
)
from modules.customer_portal.presentation.schemas.portal import (
    PortalAccessTokenOut,
    PortalLoginRequest,
    PortalRefreshRequest,
    PortalTokenResponse,
)

router = APIRouter()

# A separate bucket from core.rbac.rate_limit.login_rate_limiter (staff
# login) so a burst of portal login attempts from one IP never throttles a
# staff member logging in from the same office network, and vice versa.
portal_login_rate_limiter = FixedWindowRateLimiter(max_requests=10, window_seconds=60)

_REFRESH_COOKIE_PATH = "/api/v1/customer_portal/auth"


def _set_portal_cookies(response: Response, *, access_token: str, refresh_token: Optional[str]) -> None:
    response.set_cookie(
        CUSTOMER_ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
    )
    if refresh_token:
        response.set_cookie(
            CUSTOMER_REFRESH_TOKEN_COOKIE_NAME,
            refresh_token,
            max_age=settings.refresh_token_expire_days * 86400,
            path=_REFRESH_COOKIE_PATH,
            httponly=True,
            secure=settings.environment != "development",
            samesite="lax",
        )


def _clear_portal_cookies(response: Response) -> None:
    response.delete_cookie(CUSTOMER_ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(CUSTOMER_REFRESH_TOKEN_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)


@router.post("/auth/login", response_model=PortalTokenResponse)
def login(payload: PortalLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> PortalTokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    portal_login_rate_limiter.check(client_ip)
    login_row = auth_service.authenticate_customer(db, email=payload.email, password=payload.password)
    access_token, refresh_token = auth_service.issue_login_tokens(db, login=login_row)
    db.commit()
    _set_portal_cookies(response, access_token=access_token, refresh_token=refresh_token)
    return PortalTokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/refresh", response_model=PortalAccessTokenOut)
def refresh(
    request: Request,
    response: Response,
    payload: Optional[PortalRefreshRequest] = None,
    db: Session = Depends(get_db),
) -> PortalAccessTokenOut:
    refresh_token = (payload.refresh_token if payload else None) or request.cookies.get(
        CUSTOMER_REFRESH_TOKEN_COOKIE_NAME
    )
    if not refresh_token:
        raise UnauthenticatedError("Missing refresh token")
    access_token = auth_service.refresh_access_token(db, refresh_token=refresh_token)
    _set_portal_cookies(response, access_token=access_token, refresh_token=None)
    return PortalAccessTokenOut(access_token=access_token)


@router.post("/auth/logout")
def logout(request: Request, response: Response, payload: Optional[PortalRefreshRequest] = None) -> dict:
    refresh_token = (payload.refresh_token if payload else None) or request.cookies.get(
        CUSTOMER_REFRESH_TOKEN_COOKIE_NAME
    )
    if refresh_token:
        auth_service.logout_everywhere(refresh_token=refresh_token)
    _clear_portal_cookies(response)
    return {"status": "ok"}
