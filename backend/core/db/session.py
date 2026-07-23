from contextvars import ContextVar
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Published by core/api/middleware.py's CompanyContextMiddleware for the
# duration of one request; read by the `after_begin` hook below so every
# transaction opened on the engine's Postgres connection carries the
# caller's company as a session variable, backing the Row-Level-Security
# policies created in the migration enabling RLS. None outside a request
# (migrations, seed scripts, background jobs) -- those run as the
# table-owning role, which Postgres exempts from RLS by default, so leaving
# it unset there is intentional, not an oversight.
current_company_id_var: ContextVar[Optional[str]] = ContextVar("current_company_id", default=None)


@event.listens_for(SessionLocal, "after_begin")
def _apply_rls_company_context(session: Session, transaction, connection) -> None:
    if connection.dialect.name != "postgresql":
        return
    company_id = current_company_id_var.get()
    if company_id:
        connection.execute(text("SET LOCAL app.current_company_id = :company_id"), {"company_id": company_id})


def set_company_context(db: Session, company_id: str) -> None:
    """Explicitly sets the RLS-scoping session variable on `db`'s current
    transaction -- for callers (scripts, background jobs) that run outside
    an HTTP request and therefore never pass through
    CompanyContextMiddleware/`current_company_id_var`. Ordinary request
    handling does not need to call this: `_apply_rls_company_context` above
    already does it automatically from the contextvar.

    Backed by Postgres `current_setting('app.current_company_id')` in production.
    No-op on SQLite (used only for local dev/tests where RLS isn't available);
    application-layer company_id filtering still applies regardless.
    """
    if engine.dialect.name == "postgresql":
        db.execute(text("SET LOCAL app.current_company_id = :company_id"), {"company_id": company_id})


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
