from core.db.session import db_session
from core.events.event_envelope import Event
from core.events.models import EventLogEntry


def persist_event(event: Event) -> None:
    with db_session() as db:
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
