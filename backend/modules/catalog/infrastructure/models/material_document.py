from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class MaterialDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links a Material to an uploaded document (technical PDF, installation
    guide, cleaning guide), stored via the same core documents endpoint as
    images and CRM attachments."""

    __tablename__ = "catalog_material_documents"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(GUID(), ForeignKey("documents.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
