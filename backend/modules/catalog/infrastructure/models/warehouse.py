from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS


class Warehouse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical storage location. A company may operate multiple
    warehouses; each Slab belongs to exactly one."""

    __tablename__ = "catalog_warehouses"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_ENTITY_STATUS, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
