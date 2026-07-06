import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, message: Message) -> Message:
        self.db.add(message)
        self.db.flush()
        return message

    def get(self, *, company_id: uuid.UUID, message_id: uuid.UUID) -> Optional[Message]:
        return self.db.scalar(
            select(Message).where(Message.id == message_id, Message.company_id == company_id)
        )

    def list_for_conversation(
        self, *, company_id: uuid.UUID, conversation_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.company_id == company_id, Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
