from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class MaterialImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links a Material to an uploaded image (stored via the core documents
    endpoint, per the existing shared-storage pattern -- this module does
    not reinvent file storage). `image_type` distinguishes full-resolution
    gallery shots, the thumbnail, and bookmatch pair images."""

    __tablename__ = "catalog_material_images"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(GUID(), ForeignKey("documents.id"), nullable=False, index=True)
    image_type: Mapped[str] = mapped_column(String, nullable=False, default="gallery")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
