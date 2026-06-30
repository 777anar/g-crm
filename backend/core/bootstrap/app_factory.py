"""Builds the FastAPI app: mounts core routers, registers error handlers and
middleware, then mounts whatever business modules are installed (which may
be none -- the core must run standalone, per the frozen architecture's "core
must never depend on any business module" requirement).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api.errors import register_error_handlers
from core.api.middleware import RequestIDMiddleware
from core.auth.router import router as auth_router
from core.companies.router import router as companies_router
from core.config import settings
from core.events.router import router as events_router
from core.module_registry.registry import register_modules
from core.storage.router import router as documents_router


def create_app() -> FastAPI:
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
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    # Core routers -- always present, regardless of which modules are installed.
    app.include_router(auth_router)
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
