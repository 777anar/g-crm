from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class MaterialThickness(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One thickness option available for a Material ("Stone") -- e.g. a
    Calacatta Gold slab might be offered in 12mm and 20mm. Normalizes what
    used to be a single free-text `thickness_mm` column on the Material
    itself (kept, unused by new selections, for backward compatibility) into
    a real Brand -> Stone -> Thickness -> Size selection chain (Sprint 4).
    Deliberately just the thickness value -- no manufacturer technical
    specs (weight, finish-per-thickness, etc.) are stored here."""

    __tablename__ = "catalog_material_thicknesses"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=False, index=True)
    thickness_mm: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
