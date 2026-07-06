from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class MessageTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A reusable canned message. Covers both "message templates" (formal,
    often channel-specific wording) and "quick replies" (short, shortcut-
    triggered snippets) as one entity distinguished only by whether
    `shortcut` is set -- two nearly-identical tables would only duplicate
    the same CRUD for no real behavioral difference. channel_type is
    nullable: null means usable on any channel."""

    __tablename__ = "communication_message_templates"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    channel_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    shortcut: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
