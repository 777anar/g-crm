from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.installation.domain.value_objects import JOB_STATUS_SCHEDULED


class InstallationJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A crew's on-site installation job for one Order."""

    __tablename__ = "installation_jobs"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=False, index=True, unique=True)

    job_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=JOB_STATUS_SCHEDULED, index=True)

    crew_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("installation_crews.id"), nullable=True, index=True)
    scheduled_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    scheduled_time_slot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    route_sequence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    started_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
