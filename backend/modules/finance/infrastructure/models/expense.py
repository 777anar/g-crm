from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.finance.domain.value_objects import EXPENSE_CATEGORY_OTHER


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A company or order-linked cost entry (materials, labor, transport,
    ...). order_id is optional -- general overhead has none."""

    __tablename__ = "expenses"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=True, index=True)

    category: Mapped[str] = mapped_column(String(20), nullable=False, default=EXPENSE_CATEGORY_OTHER, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AZN")
    expense_date: Mapped[str] = mapped_column(String(10), nullable=False)

    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
