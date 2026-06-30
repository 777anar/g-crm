"""In-process publish/subscribe event bus (Phase 1 implementation).

Per the frozen architecture: the bus is generic infrastructure that knows
nothing about specific event names. Modules register subscriptions (via
their manifest's `event_subscriptions`) at startup; publishing modules call
`event_bus.publish(event, db)` without knowing who, if anyone, is listening.

Upgrade path: this class's public interface (`publish`, `subscribe`) is the
contract. A future swap to Redis Pub/Sub or Celery-carried events would
implement the same interface without callers changing.
"""
import logging
from collections import defaultdict
from typing import Callable, Dict, List

from sqlalchemy.orm import Session

from core.events.event_envelope import Event

logger = logging.getLogger("core.events")

EventHandler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].append(handler)

    def publish(self, event: Event, db: Session) -> None:
        """`db` is the caller's own active session (the same one used for the
        business write that triggered this event). Persisting through it --
        rather than opening a second connection -- keeps the event log entry
        part of the same transaction as the write, and avoids a writer-lock
        conflict with SQLite (a second connection cannot write while the
        first transaction is still open) and avoids torn reads on any
        backend if the outer transaction later rolls back."""
        if event.company_id is None:
            raise ValueError(
                f"Refusing to publish event '{event.name}' without a company_id. "
                "All events must be tenant-scoped."
            )
        self._persist(event, db)
        handlers = self._subscribers.get(event.name, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed while processing %s (event_id=%s)",
                    getattr(handler, "__name__", repr(handler)),
                    event.name,
                    event.event_id,
                )

    def _persist(self, event: Event, db: Session) -> None:
        from core.events.models import EventLogEntry

        db.add(
            EventLogEntry(
                id=event.event_id,
                event_name=event.name,
                company_id=event.company_id,
                payload=event.payload,
                published_by_module=event.published_by_module,
                processed_by=[],
                occurred_at=event.occurred_at,
            )
        )
        db.flush()


event_bus = EventBus()
