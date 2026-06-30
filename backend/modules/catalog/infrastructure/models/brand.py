from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS


class Brand(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A stone brand carried by a company's catalog (e.g. NEOLITH,
    CAESARSTONE, INALCO). Company-scoped: two companies may both carry
    NEOLITH, each with their own Brand row, their own Collections, and
    their own pricing."""

    __tablename__ = "catalog_brands"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_document_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_ENTITY_STATUS, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
