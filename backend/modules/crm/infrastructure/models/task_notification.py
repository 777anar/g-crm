from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class TaskNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An in-app notification about a Task event (assigned, reassigned,
    reminder due, overdue) for one user. Mirrors Installation's Notification
    model exactly -- no email/SMS delivery exists in this codebase yet, so
    this is the real, working slice of "notifications": created
    synchronously and surfaced in-app."""

    __tablename__ = "crm_task_notifications"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[str] = mapped_column(GUID(), ForeignKey("crm_tasks.id"), nullable=False, index=True)
    read_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
