from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.rate_limit import FixedWindowRateLimiter
from modules.customer_portal.application import auth_service
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


@router.post("/auth/login", response_model=PortalTokenResponse)
def login(payload: PortalLoginRequest, request: Request, db: Session = Depends(get_db)) -> PortalTokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    portal_login_rate_limiter.check(client_ip)
    login_row = auth_service.authenticate_customer(db, email=payload.email, password=payload.password)
    access_token, refresh_token = auth_service.issue_login_tokens(db, login=login_row)
    db.commit()
    return PortalTokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/refresh", response_model=PortalAccessTokenOut)
def refresh(payload: PortalRefreshRequest, db: Session = Depends(get_db)) -> PortalAccessTokenOut:
    access_token = auth_service.refresh_access_token(db, refresh_token=payload.refresh_token)
    return PortalAccessTokenOut(access_token=access_token)


@router.post("/auth/logout")
def logout(payload: PortalRefreshRequest) -> dict:
    auth_service.logout_everywhere(refresh_token=payload.refresh_token)
    return {"status": "ok"}
