"""Customer-token JWT issuance. A deliberate parallel to
core/auth/security.py's create_access_token/create_refresh_token, not a
reuse of them: those functions hardcode a `sub` = staff `users.id` and a
`role`/`module_permissions` shape that has no meaning for a customer login.
Keeping token creation separate (while still reusing decode_token,
hash_password, verify_password, and the token_denylist -- all generic
primitives with no staff-specific shape) means a customer token and a staff
token can never be confused for one another: the `type` claim differs
("customer_access"/"customer_refresh" vs "access"/"refresh"), and
get_current_customer (customer_portal's own dependency) checks it, exactly
as core/rbac/dependencies.get_current_user checks its own type."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt

from core.config import settings

CUSTOMER_ACCESS_TOKEN_TYPE = "customer_access"
CUSTOMER_REFRESH_TOKEN_TYPE = "customer_refresh"

# httpOnly cookie names the Customer Portal frontend authenticates with
# (Phase 18) -- a separate namespace from core/auth/security.py's staff
# cookies, matching the separate localStorage keys the frontend already used
# (lib/portal-session.ts) so a customer and a staff member can be signed in
# on the same browser at once without collision.
CUSTOMER_ACCESS_TOKEN_COOKIE_NAME = "g_erp_portal_access_token"
CUSTOMER_REFRESH_TOKEN_COOKIE_NAME = "g_erp_portal_refresh_token"


def _create_token(data: Dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_customer_access_token(*, customer_login_id: uuid.UUID, customer_id: uuid.UUID, company_id: uuid.UUID) -> str:
    payload = {
        "sub": str(customer_login_id),
        "customer_id": str(customer_id),
        "company_id": str(company_id),
    }
    return _create_token(payload, timedelta(minutes=settings.access_token_expire_minutes), CUSTOMER_ACCESS_TOKEN_TYPE)


def create_customer_refresh_token(*, customer_login_id: uuid.UUID, generation: int = 0) -> str:
    return _create_token(
        {"sub": str(customer_login_id), "gen": generation},
        timedelta(days=settings.refresh_token_expire_days),
        CUSTOMER_REFRESH_TOKEN_TYPE,
    )
