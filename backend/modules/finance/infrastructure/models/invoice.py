from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.finance.domain.value_objects import INVOICE_STATUS_DRAFT


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An invoice raised against one Order, optionally linked to the
    Installation job that triggered it. company_id/customer_id are
    denormalized from the Order (same pattern Order uses for customer_id
    from its Project) so invoice listing/filtering never needs a join."""

    __tablename__ = "invoices"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=False, index=True, unique=True)
    customer_id: Mapped[str] = mapped_column(GUID(), ForeignKey("crm_customers.id"), nullable=False, index=True)
    installation_job_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("installation_jobs.id"), nullable=True, index=True
    )

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=INVOICE_STATUS_DRAFT, index=True)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AZN")
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))

    issue_date: Mapped[str] = mapped_column(String(10), nullable=False)
    due_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sent_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    @property
    def balance_due(self) -> Decimal:
        return self.total_amount - self.amount_paid
