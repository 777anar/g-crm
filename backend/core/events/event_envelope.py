import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class Event:
    """Generic event envelope. The core knows nothing about specific event
    names (LeadCreated, OrderApproved, ...) -- those are defined by each
    module's own `domain/events.py`. company_id is mandatory: the bus refuses
    to dispatch any event missing tenant context (see EventBus.publish)."""

    name: str
    company_id: uuid.UUID
    payload: Dict[str, Any]
    published_by_module: str
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
