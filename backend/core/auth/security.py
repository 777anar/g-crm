import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# httpOnly cookie names the browser frontend authenticates with (Phase 18).
# Defined here rather than in core/auth/router.py so core/rbac/dependencies.py
# can read them too without an import cycle (router.py already depends on
# core/rbac/dependencies.py for CurrentUser/get_current_user).
ACCESS_TOKEN_COOKIE_NAME = "g_erp_access_token"
REFRESH_TOKEN_COOKIE_NAME = "g_erp_refresh_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def _create_token(data: Dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    *,
    user_id: uuid.UUID,
    active_company_id: Optional[uuid.UUID],
    role: Optional[str],
    module_permissions: Optional[Dict[str, List[str]]] = None,
) -> str:
    payload = {
        "sub": str(user_id),
        "active_company_id": str(active_company_id) if active_company_id else None,
        "role": role,
        "module_permissions": module_permissions or {},
    }
    return _create_token(payload, timedelta(minutes=settings.access_token_expire_minutes), "access")


def create_refresh_token(*, user_id: uuid.UUID, generation: int = 0) -> str:
    # `gen` pins this token to the user's revocation generation at issue
    # time -- refresh_access_token rejects it once that generation is stale
    # (see core/auth/token_denylist.py). A monotonic counter avoids the
    # same-second race a wall-clock revocation cutoff would have against a
    # token issued (e.g. by an immediate re-login) within the same second.
    return _create_token(
        {"sub": str(user_id), "gen": generation},
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
