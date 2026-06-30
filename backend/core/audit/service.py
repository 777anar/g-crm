import uuid
from typing import Optional

from sqlalchemy.orm import Session

from core.audit.models import AuditLog


def record_audit(
    db: Session,
    *,
    company_id: uuid.UUID,
    module: str,
    actor_user_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    diff: Optional[dict] = None,
) -> AuditLog:
    """Writes one append-only audit entry. Callable by any module's use-cases."""
    entry = AuditLog(
        company_id=company_id,
        module=module,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        diff_json=diff,
    )
    db.add(entry)
    return entry
