from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crm_customers"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False, default="individual")
    primary_contact_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("crm_contacts.id"), nullable=True
    )
    assigned_manager_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    lead_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    advertising_campaign: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    deleted_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = ()
