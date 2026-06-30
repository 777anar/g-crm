from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS


class Collection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named line/collection within a Brand (e.g. NEOLITH's "Calacatta"
    collection). Materials belong to a Collection within a Brand."""

    __tablename__ = "catalog_collections"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    brand_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_brands.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_ENTITY_STATUS, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
