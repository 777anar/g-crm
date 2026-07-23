import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from core.api.errors import UnauthenticatedError
from core.auth.security import decode_token
from modules.customer_portal.infrastructure.security import (
    CUSTOMER_ACCESS_TOKEN_COOKIE_NAME,
    CUSTOMER_ACCESS_TOKEN_TYPE,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/customer_portal/auth/login", auto_error=False)


@dataclass
class CurrentCustomer:
    customer_login_id: uuid.UUID
    customer_id: uuid.UUID
    company_id: uuid.UUID


def get_current_customer(request: Request, token: Optional[str] = Depends(oauth2_scheme)) -> CurrentCustomer:
    raw_token = token or request.cookies.get(CUSTOMER_ACCESS_TOKEN_COOKIE_NAME)
    if not raw_token:
        raise UnauthenticatedError("Missing or invalid access token")
    try:
        payload = decode_token(raw_token)
    except ValueError as exc:
        raise UnauthenticatedError(str(exc)) from exc
    if payload.get("type") != CUSTOMER_ACCESS_TOKEN_TYPE:
        raise UnauthenticatedError("Token is not a customer portal access token")
    return CurrentCustomer(
        customer_login_id=uuid.UUID(payload["sub"]),
        customer_id=uuid.UUID(payload["customer_id"]),
        company_id=uuid.UUID(payload["company_id"]),
    )
