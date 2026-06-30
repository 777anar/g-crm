from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.events.models import EventLogEntry
from core.rbac.dependencies import CurrentUser, get_current_user
from core.api.errors import ForbiddenError

router = APIRouter(prefix="/api/v1/core/events", tags=["core:events"])


@router.get("")
def list_events(
    event_name: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> List[dict]:
    """Read-only observability into the event log. Owner/admin only -- events
    are an internal integration mechanism, never published via a public API
    (per API_SPECIFICATION.md section 9)."""
    if current_user.role != "owner":
        raise ForbiddenError("Only company owners may inspect the event log")

    stmt = select(EventLogEntry).where(EventLogEntry.company_id == current_user.active_company_id)
    if event_name:
        stmt = stmt.where(EventLogEntry.event_name == event_name)
    stmt = stmt.order_by(EventLogEntry.occurred_at.desc()).limit(100)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(r.id),
            "event_name": r.event_name,
            "payload": r.payload,
            "published_by_module": r.published_by_module,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
        }
        for r in rows
    ]
