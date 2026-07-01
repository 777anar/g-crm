from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class QuoteSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sales_quote_sections"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    quote_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_quotes.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    total_measured_area: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    subtotal_sale: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    subtotal_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
