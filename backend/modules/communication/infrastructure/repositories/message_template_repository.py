import uuid
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.message_template import MessageTemplate


class MessageTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, template: MessageTemplate) -> MessageTemplate:
        self.db.add(template)
        self.db.flush()
        return template

    def get(self, *, company_id: uuid.UUID, template_id: uuid.UUID) -> Optional[MessageTemplate]:
        return self.db.scalar(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id, MessageTemplate.company_id == company_id
            )
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        channel_type: Optional[str] = None,
        include_inactive: bool = True,
    ) -> List[MessageTemplate]:
        stmt = select(MessageTemplate).where(MessageTemplate.company_id == company_id)
        if channel_type:
            stmt = stmt.where(
                or_(MessageTemplate.channel_type == channel_type, MessageTemplate.channel_type.is_(None))
            )
        if not include_inactive:
            stmt = stmt.where(MessageTemplate.is_active.is_(True))
        stmt = stmt.order_by(MessageTemplate.name.asc())
        return list(self.db.scalars(stmt).all())
