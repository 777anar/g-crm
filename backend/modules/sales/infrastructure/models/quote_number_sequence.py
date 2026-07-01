from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, UUIDPrimaryKeyMixin


class QuoteNumberSequence(UUIDPrimaryKeyMixin, Base):
    """Atomic per-company per-year counter for quote numbers.

    One row per (company_id, year). `last_number` starts at 0 and is
    incremented before each new quote is issued, giving QT-YYYY-0001-v1 etc.
    """

    __tablename__ = "sales_quote_number_sequences"
    __table_args__ = (UniqueConstraint("company_id", "year", name="uq_quote_sequence"),)

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
