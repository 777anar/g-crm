from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class OrderMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_measurements"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(GUID(), ForeignKey("order_sections.id"), nullable=False, index=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    length_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    width_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    thickness_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    area_m2: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    required_area_m2: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    waste_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("10"))
    override_required_area: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
