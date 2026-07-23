import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.auth.security import decode_token
from core.db.session import current_company_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


class CompanyContextMiddleware(BaseHTTPMiddleware):
    """Best-effort-decodes the caller's access token (header or cookie,
    staff or customer portal) and publishes its company claim into a
    contextvar for the duration of the request, so `core/db/session.py`'s
    Postgres session-begin hook can `SET LOCAL app.current_company_id` before
    any query runs -- the second, Postgres-Row-Level-Security layer of
    tenant isolation described in DATABASE_DESIGN.md, on top of (never
    instead of) the application-layer `company_id` filtering every
    repository already does.

    Decoding here (rather than depending on `get_current_user`) is what lets
    one contextvar cover both staff and customer-portal auth without this
    middleware needing to know about `require_permission` or any
    module-specific dependency graph -- it only ever reads a claim, it never
    authenticates or authorizes anything; `get_current_user`/
    `get_current_customer` remain the sole source of truth for that."""

    async def dispatch(self, request: Request, call_next):
        company_id = self._extract_company_id(request)
        token = current_company_id_var.set(company_id)
        try:
            return await call_next(request)
        finally:
            current_company_id_var.reset(token)

    @staticmethod
    def _extract_company_id(request: Request):
        raw_token = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            raw_token = auth_header[7:]
        if not raw_token:
            raw_token = request.cookies.get("g_erp_access_token") or request.cookies.get(
                "g_erp_portal_access_token"
            )
        if not raw_token:
            return None
        try:
            payload = decode_token(raw_token)
        except ValueError:
            return None
        return payload.get("active_company_id") or payload.get("company_id")
