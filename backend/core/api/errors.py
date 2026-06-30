"""Uniform error format, per API_SPECIFICATION.md section 6. Every module
raises these exceptions; the core's exception handlers (registered once in
app_factory.py) translate them into the standard envelope -- no module needs
to know about the envelope shape itself.
"""
import uuid
from typing import Any, List, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: Optional[List[dict]] = None):
        self.message = message
        self.details = details or []
        super().__init__(message)


class ValidationAPIError(APIError):
    status_code = 400
    code = "VALIDATION_ERROR"


class UnauthenticatedError(APIError):
    status_code = 401
    code = "UNAUTHENTICATED"


class ForbiddenError(APIError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(APIError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(APIError):
    status_code = 409
    code = "CONFLICT"


class BusinessRuleViolationError(APIError):
    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"


class RateLimitedError(APIError):
    status_code = 429
    code = "RATE_LIMITED"


def _envelope(code: str, message: str, details: List[dict], request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "details": details, "request_id": request_id}}


def register_error_handlers(app) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details, request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        details = [
            {"field": ".".join(str(p) for p in err["loc"][1:]), "issue": err["msg"]} for err in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content=_envelope("VALIDATION_ERROR", "Request validation failed", details, request_id),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=500,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred", [], request_id),
        )
