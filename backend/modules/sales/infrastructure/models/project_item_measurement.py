from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.sales.domain.value_objects import MEASUREMENT_STATUS_DRAFT


class ProjectItemMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One on-site measurement revision for a Project Item. Revisions are
    never edited in place once a later one exists -- a re-measure creates a
    new row with the next `revision_number`, so the original site visit's
    numbers are never lost (mirrors the Quote versioning pattern)."""

    __tablename__ = "sales_project_item_measurements"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    project_item_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_project_items.id"), nullable=False, index=True)

    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=MEASUREMENT_STATUS_DRAFT)

    length_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 1), nullable=True)
    width_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 1), nullable=True)
    thickness_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 1), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    area_m2: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)

    measurer_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    measured_at: Mapped[Optional[object]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    customer_signature_document_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("documents.id"), nullable=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
