import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.integration_log_entry import IntegrationLogEntry


class IntegrationLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, entry: IntegrationLogEntry) -> IntegrationLogEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def list(
        self,
        *,
        company_id: Optional[uuid.UUID],
        channel_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = 100,
    ) -> List[IntegrationLogEntry]:
        stmt = select(IntegrationLogEntry)
        if company_id is not None:
            stmt = stmt.where(IntegrationLogEntry.company_id == company_id)
        if channel_id is not None:
            stmt = stmt.where(IntegrationLogEntry.channel_id == channel_id)
        if provider:
            stmt = stmt.where(IntegrationLogEntry.provider == provider)
        if direction:
            stmt = stmt.where(IntegrationLogEntry.direction == direction)
        stmt = stmt.order_by(IntegrationLogEntry.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())
