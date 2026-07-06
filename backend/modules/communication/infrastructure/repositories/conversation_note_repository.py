import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.conversation_note import ConversationNote


class ConversationNoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, note: ConversationNote) -> ConversationNote:
        self.db.add(note)
        self.db.flush()
        return note

    def list_for_conversation(self, *, company_id: uuid.UUID, conversation_id: uuid.UUID) -> List[ConversationNote]:
        stmt = (
            select(ConversationNote)
            .where(ConversationNote.company_id == company_id, ConversationNote.conversation_id == conversation_id)
            .order_by(ConversationNote.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())
