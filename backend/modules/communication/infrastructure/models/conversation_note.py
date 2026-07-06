from typing import Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class ConversationNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An internal, customer-invisible note attached to a Conversation --
    the Communication Center's equivalent of CRM's Customer notes."""

    __tablename__ = "communication_conversation_notes"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("communication_conversations.id"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
