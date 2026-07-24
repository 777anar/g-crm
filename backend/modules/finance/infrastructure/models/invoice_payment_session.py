from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.finance.domain.value_objects import PAYMENT_SESSION_STATUS_PENDING


class InvoicePaymentSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One Customer-Portal-initiated checkout attempt against one Invoice's
    full outstanding balance. Tracks the gateway's own session id so a later
    webhook callback (which only ever supplies a provider session id, never
    our internal one) can be correlated back to this row -- and, once
    completed, to the `Payment` row `RecordPaymentUseCase` creates for it."""

    __tablename__ = "invoice_payment_sessions"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(GUID(), ForeignKey("invoices.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(GUID(), ForeignKey("crm_customers.id"), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_session_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PAYMENT_SESSION_STATUS_PENDING, index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    checkout_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    payment_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("invoice_payments.id"), nullable=True)
    completed_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
