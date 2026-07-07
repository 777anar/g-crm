from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def set_company_context(db: Session, company_id: str) -> None:
    """Sets the RLS-scoping session variable for the current transaction.

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
