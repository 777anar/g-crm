from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.sales.domain.value_objects import (
    DISCOUNT_TYPE_NONE,
    QUOTE_STATUS_DRAFT,
)


class Quote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sales_quotes"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_projects.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(GUID(), ForeignKey("crm_customers.id"), nullable=False, index=True)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    quote_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=QUOTE_STATUS_DRAFT, index=True)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AZN")
    price_list_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_price_lists.id"), nullable=True)
    valid_until: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # ISO date string

    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prepared_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    sent_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Computed totals — recomputed on every line-item change.
    subtotal_gross: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False, default=DISCOUNT_TYPE_NONE)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    subtotal_after_discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("18"))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total_final: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total_internal_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    profit_margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
