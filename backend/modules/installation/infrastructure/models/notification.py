from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An in-app notification about an Installation Job event (assigned,
    rescheduled, status changed) for one user. No email/SMS delivery exists
    in this codebase yet -- this is the real, working slice of
    "notifications": it's created synchronously and surfaced in-app."""

    __tablename__ = "installation_notifications"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    installation_job_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("installation_jobs.id"), nullable=True, index=True
    )
    read_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
