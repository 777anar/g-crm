"""Shared helper for creating in-app notifications when a job is assigned,
rescheduled, or changes status. Not exposed as its own use case/endpoint --
every Installation job use case calls this as a side effect, the same way
Orders' use cases call record_audit/event_bus directly rather than through
a separate "audit use case"."""
import uuid

from sqlalchemy.orm import Session

from modules.installation.infrastructure.models.notification import Notification
from modules.installation.infrastructure.repositories.crew_repository import CrewMemberRepository


def notify_crew(
    db: Session,
    *,
    company_id: uuid.UUID,
    crew_id: uuid.UUID,
    notification_type: str,
    title: str,
    message: str,
    installation_job_id: uuid.UUID,
) -> None:
    members = CrewMemberRepository(db).list_for_crew(company_id=company_id, crew_id=crew_id)
    for member in members:
        db.add(Notification(
            company_id=company_id,
            user_id=member.user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            installation_job_id=installation_job_id,
        ))
    db.flush()
