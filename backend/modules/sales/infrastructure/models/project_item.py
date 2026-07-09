from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.sales.domain.value_objects import ITEM_TYPE_OTHER


class ProjectItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical piece ("Məmulat") within a Room -- a kitchen countertop, an
    island, a sink, ... This is the project-planning record of what's being
    made; a Quote's QuoteSectionItem is the commercial/pricing line for it and
    is created independently (a Project Item is not required to have a
    matching Quote line, and vice versa, since a Quote can be built before
    every Room/Item is finalized on site)."""

    __tablename__ = "sales_project_items"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_projects.id"), nullable=False, index=True)
    room_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_rooms.id"), nullable=False, index=True)

    item_type: Mapped[str] = mapped_column(String(50), nullable=False, default=ITEM_TYPE_OTHER)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Material selection is always Brand -> Stone -> Thickness -> Size via an
    # existing catalog StoneMaterial (never free text) -- see catalog. The
    # Stone (material_id) can offer several thickness/size options (Sprint 4's
    # normalized catalog_material_thicknesses/catalog_material_sizes); these
    # two columns record which specific option this Item was built with.
    material_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=True, index=True)
    material_thickness_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("catalog_material_thicknesses.id"), nullable=True, index=True
    )
    material_size_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("catalog_material_sizes.id"), nullable=True, index=True
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    unit: Mapped[str] = mapped_column(String(10), nullable=False, default="unit")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    production_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    installation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
