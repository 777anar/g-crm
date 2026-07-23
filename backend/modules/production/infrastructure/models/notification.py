from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An in-app notification about a Work Order event (operator assigned,
    marked urgent, stage changed) for one user (Phase 19: Stone Fabrication
    Workflow, Phase 3). Mirrors modules/installation/infrastructure/models/
    notification.py's shape exactly -- same "no email/SMS yet, created
    synchronously, surfaced in-app" scope."""

    __tablename__ = "production_notifications"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    work_order_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("work_orders.id"), nullable=True, index=True
    )
    read_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
