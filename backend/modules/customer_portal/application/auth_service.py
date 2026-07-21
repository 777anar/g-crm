"""Customer login/refresh/logout orchestration -- a deliberate mirror of
core/auth/service.py's authenticate_user/issue_login_tokens/
refresh_access_token/logout_everywhere, scoped to CustomerLogin instead of
User. Plain functions rather than a use-case class, matching core/auth's own
choice: login/refresh/logout are not audited business writes (same as staff
login), so they don't need the record_audit/event_bus ceremony
access_use_cases.py's actual portal-access-management writes do."""
import uuid
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import UnauthenticatedError
from core.auth.security import decode_token, verify_password
from core.auth.token_denylist import token_denylist
from modules.customer_portal.infrastructure.models.customer_login import CustomerLogin
from modules.customer_portal.infrastructure.security import (
    CUSTOMER_REFRESH_TOKEN_TYPE,
    create_customer_access_token,
    create_customer_refresh_token,
)


def authenticate_customer(db: Session, *, email: str, password: str) -> CustomerLogin:
    login = db.scalar(select(CustomerLogin).where(CustomerLogin.email == email))
    if login is None or not login.is_active or not verify_password(password, login.password_hash):
        raise UnauthenticatedError("Invalid email or password")
    return login


def issue_login_tokens(db: Session, *, login: CustomerLogin) -> Tuple[str, str]:
    login.last_login_at = datetime.now(timezone.utc)
    db.flush()
    access_token = create_customer_access_token(
        customer_login_id=login.id, customer_id=login.customer_id, company_id=login.company_id
    )
    generation = token_denylist.current_generation(str(login.id))
    refresh_token = create_customer_refresh_token(customer_login_id=login.id, generation=generation)
    return access_token, refresh_token


def refresh_access_token(db: Session, *, refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise UnauthenticatedError("Invalid or expired refresh token") from exc
    if payload.get("type") != CUSTOMER_REFRESH_TOKEN_TYPE:
        raise UnauthenticatedError("Token is not a customer portal refresh token")
    login_id = uuid.UUID(payload["sub"])
    if token_denylist.is_revoked(str(login_id), int(payload.get("gen", 0))):
        raise UnauthenticatedError("Refresh token has been revoked")
    login = db.get(CustomerLogin, login_id)
    if login is None or not login.is_active:
        raise UnauthenticatedError("Portal access is no longer active")
    return create_customer_access_token(
        customer_login_id=login.id, customer_id=login.customer_id, company_id=login.company_id
    )


def logout_everywhere(*, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        return
    if payload.get("type") != CUSTOMER_REFRESH_TOKEN_TYPE:
        return
    token_denylist.revoke_all(payload["sub"])
