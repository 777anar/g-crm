from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.communication.domain.value_objects import DEFAULT_MESSAGE_TYPE


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One message within a Conversation, in either direction."""

    __tablename__ = "communication_messages"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("communication_conversations.id"), nullable=False, index=True
    )

    direction: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(String(10), nullable=False)
    sender_user_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    message_type: Mapped[str] = mapped_column(String(20), nullable=False, default=DEFAULT_MESSAGE_TYPE)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("communication_message_templates.id"), nullable=True
    )

    external_message_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")
