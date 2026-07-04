from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class InstallationPhoto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links an Installation Job to an uploaded photo (stored via the core
    documents endpoint, per the existing shared-storage pattern -- see
    modules/catalog/infrastructure/models/material_image.py for the same
    idea). `photo_type` includes "signature": the customer's captured
    signature is just a photo row, not a separate entity."""

    __tablename__ = "installation_photos"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    installation_job_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("installation_jobs.id"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(GUID(), ForeignKey("documents.id"), nullable=False, index=True)
    photo_type: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    caption: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
