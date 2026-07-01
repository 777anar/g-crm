from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.orders.domain.value_objects import ORDER_STATUS_WAITING


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_projects.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(GUID(), ForeignKey("crm_customers.id"), nullable=False, index=True)
    quote_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_quotes.id"), nullable=False, index=True)

    order_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=ORDER_STATUS_WAITING, index=True)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AZN")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    production_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    installation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    scheduled_production_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    scheduled_installation_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    completed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    # Financial snapshot from quote
    subtotal_gross: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    discount_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    subtotal_after_discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("18"))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total_final: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total_internal_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
