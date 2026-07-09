from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class MaterialSize(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One slab size option available for a Material ("Stone") -- e.g.
    "3200x1600mm". Normalizes what used to be a single free-text
    `dimensions` column on the Material itself (kept, unused by new
    selections, for backward compatibility) into a real
    Brand -> Stone -> Thickness -> Size selection chain (Sprint 4).
    Deliberately just the size value -- no manufacturer technical specs are
    stored here."""

    __tablename__ = "catalog_material_sizes"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=False, index=True)
    dimensions: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
