from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, UUIDPrimaryKeyMixin


class InvoiceNumberSequence(UUIDPrimaryKeyMixin, Base):
    """Atomic per-company per-year counter for invoice numbers."""

    __tablename__ = "invoice_number_sequences"
    __table_args__ = (UniqueConstraint("company_id", "year", name="uq_invoice_sequence"),)

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
