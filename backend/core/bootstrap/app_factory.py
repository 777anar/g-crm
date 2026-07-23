"""Builds the FastAPI app: mounts core routers, registers error handlers and
middleware, then mounts whatever business modules are installed (which may
be none -- the core must run standalone, per the frozen architecture's "core
must never depend on any business module" requirement).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api.errors import register_error_handlers
from core.api.middleware import CompanyContextMiddleware, RequestIDMiddleware
from core.audit.router import router as audit_router
from core.auth.router import router as auth_router
from core.companies.router import router as companies_router
from core.config import settings
from core.events.router import router as events_router
from core.module_registry.registry import register_modules
from core.storage.router import router as documents_router

DEFAULT_JWT_SECRET = "dev-secret-change-me"
DEFAULT_CHANNEL_CREDENTIALS_KEY = "dev-channel-credentials-key-change-me"


def _guard_against_insecure_defaults() -> None:
    """Refuses to boot outside development with a placeholder secret still
    in place. Covers every secret whose default value is public (it's right
    here in the source): the JWT secret would make every access/refresh
    token forgeable; the channel-credentials key would mean every stored
    WhatsApp/Twilio/SMTP/IMAP credential (modules/communication) is
    "encrypted" with a key anyone reading this file already has -- as good
    as plaintext."""
    if settings.environment == "development":
        return
    if settings.jwt_secret_key == DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "Refusing to start: JWT_SECRET_KEY is still the default placeholder value "
            f"('{DEFAULT_JWT_SECRET}') outside of a development environment "
            f"(ENVIRONMENT={settings.environment!r}). Set a real secret via the JWT_SECRET_KEY "
            "environment variable before deploying."
        )
    if settings.channel_credentials_encryption_key == DEFAULT_CHANNEL_CREDENTIALS_KEY:
        raise RuntimeError(
            "Refusing to start: CHANNEL_CREDENTIALS_ENCRYPTION_KEY is still the default "
            f"placeholder value ('{DEFAULT_CHANNEL_CREDENTIALS_KEY}') outside of a development "
            f"environment (ENVIRONMENT={settings.environment!r}). Set a real key via the "
            "CHANNEL_CREDENTIALS_ENCRYPTION_KEY environment variable before deploying."
        )


def create_app() -> FastAPI:
    _guard_against_insecure_defaults()

    app = FastAPI(
        title="G-STONE ERP API",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    app.add_middleware(CompanyContextMiddleware)

    register_error_handlers(app)

    # Core routers -- always present, regardless of which modules are installed.
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(companies_router)
    app.include_router(documents_router)
    app.include_router(events_router)

    @app.get("/api/v1/health", tags=["core:health"])
    def health() -> dict:
        return {"status": "ok"}

    # Business modules -- zero or more, discovered generically. The core
    # above this line has no knowledge of what (if anything) gets mounted here.
    register_modules(app)

    return app
