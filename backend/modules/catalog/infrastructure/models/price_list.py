from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS


class PriceList(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named, company-specific price list (e.g. "Retail 2026", "Wholesale
    - KORONA PREMIUM"). Company-scoped by construction, satisfying
    "company-specific pricing" -- the same Material can have different
    prices in different companies' price lists, or multiple price lists
    within one company (retail vs. trade, for example)."""

    __tablename__ = "catalog_price_lists"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AZN")
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_ENTITY_STATUS, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)


class PriceListEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One Material's cost/sale price within a PriceList."""

    __tablename__ = "catalog_price_list_entries"
    __table_args__ = (
        UniqueConstraint("price_list_id", "material_id", name="uq_catalog_price_entry_per_material"),
    )

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    price_list_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("catalog_price_lists.id"), nullable=False, index=True
    )
    material_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=False, index=True)
    cost_price: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    sale_price: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False, default=0)
