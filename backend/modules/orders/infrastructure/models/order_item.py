from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_items"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(GUID(), ForeignKey("order_sections.id"), nullable=False, index=True)

    item_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    material_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=True, index=True)
    slab_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_slabs.id"), nullable=True, index=True)

    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    unit: Mapped[str] = mapped_column(String(10), nullable=False, default="unit")

    unit_sale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    unit_cost_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    line_total_sale: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    line_total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    production_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    installation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
