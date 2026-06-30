from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.catalog.domain.value_objects import DEFAULT_MATERIAL_STATUS


class StoneMaterial(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A sellable stone material/design (e.g. "NEOLITH Calacatta Gold,
    12mm Polished"). This is the catalog "product" -- Slabs are the
    individually tracked physical pieces of a given Material."""

    __tablename__ = "catalog_materials"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    brand_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_brands.id"), nullable=False, index=True)
    collection_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("catalog_collections.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    material_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    finish: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    thickness_mm: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dimensions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    country_of_origin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_MATERIAL_STATUS, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
