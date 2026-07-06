from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.finance.domain.value_objects import PAYMENT_METHOD_CASH


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single payment recorded against an Invoice. An invoice can have
    several (deposit, progress, final) -- amount_paid on the Invoice is the
    running sum, recalculated each time one of these is added."""

    __tablename__ = "invoice_payments"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(GUID(), ForeignKey("invoices.id"), nullable=False, index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False, default=PAYMENT_METHOD_CASH)
    paid_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recorded_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
