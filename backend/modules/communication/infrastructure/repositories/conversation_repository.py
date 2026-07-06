import uuid
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.conversation import Conversation

# Whitelisted sortable columns -- same whitelist-not-getattr rationale as
# CustomerRepository._SORTABLE_COLUMNS / TaskRepository._SORTABLE_COLUMNS.
_SORTABLE_COLUMNS = {
    "last_message_at": Conversation.last_message_at,
    "created_at": Conversation.created_at,
    "updated_at": Conversation.updated_at,
    "status": Conversation.status,
}
DEFAULT_SORT = "-last_message_at"


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def get(self, *, company_id: uuid.UUID, conversation_id: uuid.UUID) -> Optional[Conversation]:
        return self.db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.company_id == company_id
            )
        )

    def get_by_external_contact(
        self, *, company_id: uuid.UUID, channel_id: uuid.UUID, external_contact_id: str
    ) -> Optional[Conversation]:
        return self.db.scalar(
            select(Conversation).where(
                Conversation.company_id == company_id,
                Conversation.channel_id == channel_id,
                Conversation.external_contact_id == external_contact_id,
            )
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        channel_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        assigned_to: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        lead_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Conversation]:
        stmt = select(Conversation).where(Conversation.company_id == company_id)
        if channel_id:
            stmt = stmt.where(Conversation.channel_id == channel_id)
        if status:
            stmt = stmt.where(Conversation.status == status)
        if assigned_to:
            stmt = stmt.where(Conversation.assigned_to == assigned_to)
        if customer_id:
            stmt = stmt.where(Conversation.customer_id == customer_id)
        if lead_id:
            stmt = stmt.where(Conversation.lead_id == lead_id)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Conversation.external_contact_name.ilike(pattern),
                    Conversation.external_contact_id.ilike(pattern),
                    Conversation.last_message_preview.ilike(pattern),
                )
            )

        sort = sort or DEFAULT_SORT
        descending = sort.startswith("-")
        column = _SORTABLE_COLUMNS.get(sort.lstrip("-"), Conversation.last_message_at)
        stmt = stmt.order_by(column.desc() if descending else column.asc())

        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
