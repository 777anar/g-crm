from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class CompanyServicePrice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-company default prices for work/logistics item types.

    Upsert semantics: one row per (company_id, service_key).
    Keys match SERVICE_PRICE_KEYS in value_objects.py.
    """

    __tablename__ = "company_service_prices"
    __table_args__ = (
        UniqueConstraint("company_id", "service_key", name="uq_company_service_price"),
    )

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    service_key: Mapped[str] = mapped_column(String(100), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
