import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.communication.domain.value_objects import QUEUE_STATUS_PENDING
from modules.communication.infrastructure.models.message_queue_entry import MessageQueueEntry


class MessageQueueRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, entry: MessageQueueEntry) -> MessageQueueEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def get(self, *, company_id: uuid.UUID, entry_id: uuid.UUID) -> Optional[MessageQueueEntry]:
        return self.db.scalar(
            select(MessageQueueEntry).where(
                MessageQueueEntry.id == entry_id, MessageQueueEntry.company_id == company_id
            )
        )

    def list(
        self, *, company_id: uuid.UUID, status: Optional[str] = None, limit: int = 100
    ) -> List[MessageQueueEntry]:
        stmt = select(MessageQueueEntry).where(MessageQueueEntry.company_id == company_id)
        if status:
            stmt = stmt.where(MessageQueueEntry.status == status)
        stmt = stmt.order_by(MessageQueueEntry.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_due(self, *, company_id: uuid.UUID, now: datetime, limit: int = 50) -> List[MessageQueueEntry]:
        stmt = (
            select(MessageQueueEntry)
            .where(
                MessageQueueEntry.company_id == company_id,
                MessageQueueEntry.status == QUEUE_STATUS_PENDING,
                (MessageQueueEntry.next_attempt_at.is_(None)) | (MessageQueueEntry.next_attempt_at <= now),
            )
            .order_by(MessageQueueEntry.created_at.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
