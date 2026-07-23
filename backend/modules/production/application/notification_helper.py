"""Shared helper for creating in-app notifications when a work order's
priority is marked urgent, its stage changes, or an operator is assigned to
it (Phase 19: Stone Fabrication Workflow, Phase 3). Not exposed as its own
use case/endpoint -- mirrors modules/installation/application/
notification_helper.py's `notify_crew`: every Work Order tracking use case
calls this as a side effect, the same way it already calls record_audit/
event_bus directly rather than through a separate "notification use case"."""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from modules.production.infrastructure.models.notification import Notification


def notify_user(
    db: Session,
    *,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    message: str,
    work_order_id: Optional[uuid.UUID] = None,
) -> None:
    db.add(Notification(
        company_id=company_id,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        work_order_id=work_order_id,
    ))
    db.flush()
