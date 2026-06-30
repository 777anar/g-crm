from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.catalog.domain.value_objects import DEFAULT_SLAB_STATUS


class Slab(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single, individually tracked physical piece of stone -- the unit
    that actually gets reserved, sold, and consumed in Production. Distinct
    from StoneMaterial (the sellable design/SKU): one Material may have many
    Slabs in stock across one or more Warehouses."""

    __tablename__ = "catalog_slabs"
    __table_args__ = (UniqueConstraint("company_id", "slab_number", name="uq_catalog_slab_number_per_company"),)

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_warehouses.id"), nullable=False, index=True)

    slab_number: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    rack_location: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    length_mm: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2), nullable=True)
    width_mm: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2), nullable=True)
    area_m2: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 3), nullable=True)
    weight_kg: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2), nullable=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_SLAB_STATUS, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
