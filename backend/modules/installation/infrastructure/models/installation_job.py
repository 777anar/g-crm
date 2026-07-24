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

    # E-signature integration (Phase 22) -- an alternative to manually
    # capturing a signature via the canvas SignaturePad and uploading it as
    # an InstallationPhoto: a real signature request sent via
    # core.esignature, tracked here until its webhook reports completion
    # (which then creates the completion InstallationPhoto itself, the same
    # photo_type="signature" row the manual-capture path has always used).
    signature_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    signature_provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    signature_provider_request_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
