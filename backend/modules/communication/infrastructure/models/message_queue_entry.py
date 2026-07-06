from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.communication.domain.value_objects import DEFAULT_MAX_QUEUE_ATTEMPTS, QUEUE_STATUS_PENDING


class MessageQueueEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The retry queue for one outbound Message that a real provider failed
    to send (network error, rate limit, transient 5xx). Since this codebase
    has no background job scheduler, entries are processed by an explicit
    pull -- POST /communication/queue/process, called by an admin action or
    the frontend's Queue Monitor -- the same honest pattern Tasks &
    Reminders already established for reminder/overdue notifications."""

    __tablename__ = "communication_message_queue"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(GUID(), ForeignKey("communication_messages.id"), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(GUID(), ForeignKey("communication_channels.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=QUEUE_STATUS_PENDING, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_MAX_QUEUE_ATTEMPTS)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
