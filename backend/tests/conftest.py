import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.db.base import Base
from core.companies import models as companies_models  # noqa: F401
from core.auth import models as auth_models  # noqa: F401
from core.audit import models as audit_models  # noqa: F401
from core.events import models as events_models  # noqa: F401
from core.storage import models as storage_models  # noqa: F401
from modules.crm.infrastructure import models as crm_models  # noqa: F401
from modules.catalog.infrastructure import models as catalog_models  # noqa: F401
from modules.sales.infrastructure import models as sales_models  # noqa: F401
from modules.orders.infrastructure import models as orders_models  # noqa: F401
from modules.production.infrastructure import models as production_models  # noqa: F401
from modules.installation.infrastructure import models as installation_models  # noqa: F401
from modules.finance.infrastructure import models as finance_models  # noqa: F401
from modules.communication.infrastructure import models as communication_models  # noqa: F401
from modules.ai.infrastructure import models as ai_models  # noqa: F401


@pytest.fixture()
def test_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    """A session used by the test itself for direct assertions. Bound to the
    same single StaticPool connection as every session the app creates
    during the test, so all of them see each other's committed data."""
    SessionLocal = sessionmaker(bind=test_engine, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter():
    """The login rate limiter is a module-level singleton (by design, so it
    survives across requests within one process); reset it before every test
    so tests that exercise /auth/login don't trip each other's counters."""
    from core.rbac.rate_limit import login_rate_limiter

    login_rate_limiter.reset()
    yield
    login_rate_limiter.reset()


@pytest.fixture()
def app_client(monkeypatch, test_engine, db_session):
    import core.db.session as session_module

    # Every `SessionLocal()` call (in request handlers and in the event bus's
    # own persistence path) creates a fresh Session bound to the same
    # StaticPool connection -- not the literal same Session object as
    # db_session -- so each can commit/close independently, matching real
    # request lifecycle behavior, while still sharing one underlying
    # SQLite connection so all data is visible across sessions.
    TestSessionLocal = sessionmaker(bind=test_engine, future=True)
    monkeypatch.setattr(session_module, "SessionLocal", TestSessionLocal)

    from fastapi.testclient import TestClient

    from core.bootstrap.app_factory import create_app

    app = create_app()

    def _override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    from core.db.session import get_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
