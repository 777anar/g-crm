from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class ProjectItemPhoto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A site photo attached to a Project Item. The actual file lives in the
    core documents store; this row is the link, same pattern as
    catalog.MaterialImage."""

    __tablename__ = "sales_project_item_photos"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    project_item_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_project_items.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(GUID(), ForeignKey("documents.id"), nullable=False, index=True)

    caption: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
