import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.message_attachment import MessageAttachment


class MessageAttachmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, attachment: MessageAttachment) -> MessageAttachment:
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def list_for_message(self, *, company_id: uuid.UUID, message_id: uuid.UUID) -> List[MessageAttachment]:
        stmt = (
            select(MessageAttachment)
            .where(MessageAttachment.company_id == company_id, MessageAttachment.message_id == message_id)
            .order_by(MessageAttachment.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
