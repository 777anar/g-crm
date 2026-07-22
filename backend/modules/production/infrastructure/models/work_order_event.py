from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class WorkOrderEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per change to a Work Order (status, stage, priority,
    assigned operator) -- the backbone of the "complete production
    timeline" requirement. Deliberately denormalized/human-readable
    (from_value/to_value as display strings) rather than a diff blob, so a
    timeline UI can render it directly without re-joining stage names or
    users at read time. This sits *alongside*, not instead of, the
    mandatory `core.audit_log` entry every write already records."""

    __tablename__ = "work_order_events"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("work_orders.id"), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_value: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    to_value: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    changed_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
