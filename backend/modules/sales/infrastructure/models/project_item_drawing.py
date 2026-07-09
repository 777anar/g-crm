from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.sales.domain.value_objects import DRAWING_TYPE_SKETCH


class ProjectItemDrawing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A technical drawing (DWG/DXF/sketch/PDF) attached to a Project Item.
    The actual file lives in the core documents store; this row is the
    link + categorization, same pattern as catalog.MaterialDocument."""

    __tablename__ = "sales_project_item_drawings"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    project_item_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_project_items.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(GUID(), ForeignKey("documents.id"), nullable=False, index=True)

    drawing_type: Mapped[str] = mapped_column(String(20), nullable=False, default=DRAWING_TYPE_SKETCH)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
