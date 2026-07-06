from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class InvoiceLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A snapshot line copied from the source Order's items at invoice
    creation time -- a plain description/amount pair (per DATABASE_DESIGN.md),
    not a live reference back to the order item, since an invoice is a
    point-in-time financial document."""

    __tablename__ = "invoice_lines"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(GUID(), ForeignKey("invoices.id"), nullable=False, index=True)

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
