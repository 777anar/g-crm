from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.production.domain.value_objects import DEFAULT_PRIORITY, WORK_ORDER_STATUS_QUEUED


class WorkOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A shop-floor fabrication/cutting job for one Order, consuming the
    specific Catalog slabs its slab-linked items reference."""

    __tablename__ = "work_orders"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=False, index=True, unique=True)

    work_order_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=WORK_ORDER_STATUS_QUEUED, index=True)

    assigned_to: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    scheduled_start_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    scheduled_completion_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default=DEFAULT_PRIORITY, server_default=DEFAULT_PRIORITY, index=True
    )
    current_stage_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("production_stages.id"), nullable=True, index=True
    )

    completed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
