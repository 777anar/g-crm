from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crm_contacts"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("crm_customers.id"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    deleted_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
