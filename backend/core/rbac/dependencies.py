import uuid
from dataclasses import dataclass
from typing import List, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from core.api.errors import ForbiddenError, UnauthenticatedError
from core.auth.security import decode_token
from core.rbac.permissions import role_has_permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@dataclass
class CurrentUser:
    user_id: uuid.UUID
    active_company_id: Optional[uuid.UUID]
    role: Optional[str]
    module_permissions: dict


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> CurrentUser:
    if not token:
        raise UnauthenticatedError("Missing or invalid access token")
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthenticatedError(str(exc)) from exc
    if payload.get("type") != "access":
        raise UnauthenticatedError("Token is not an access token")
    company_id = payload.get("active_company_id")
    return CurrentUser(
        user_id=uuid.UUID(payload["sub"]),
        active_company_id=uuid.UUID(company_id) if company_id else None,
        role=payload.get("role"),
        module_permissions=payload.get("module_permissions") or {},
    )


def require_permission(permission: str):
    """FastAPI dependency factory. `permission` is e.g. "crm:deals:write".
    Enforced server-side; the frontend hiding a button is never the real control.
    """

    def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.active_company_id is None:
            raise ForbiddenError("No active company selected")
        if not role_has_permission(
            role=current_user.role,
            permission=permission,
            module_permission_overrides=current_user.module_permissions,
        ):
            raise ForbiddenError(f"Missing required permission: {permission}")
        return current_user

    return _dependency


def require_active_company(current_user: CurrentUser = Depends(get_current_user)) -> uuid.UUID:
    if current_user.active_company_id is None:
        raise ForbiddenError("No active company selected")
    return current_user.active_company_id
