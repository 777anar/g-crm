from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.sales.domain.value_objects import ITEM_TYPE_OTHER


class QuoteSectionItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sales_quote_section_items"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_quote_sections.id"), nullable=False, index=True)
    quote_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_quotes.id"), nullable=False, index=True)

    item_type: Mapped[str] = mapped_column(String(50), nullable=False, default=ITEM_TYPE_OTHER)
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
