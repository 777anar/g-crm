from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crm_leads"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_channel: Mapped[str] = mapped_column(String, nullable=False, index=True)
    campaign: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="new", index=True)
    assigned_manager_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    converted_customer_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("crm_customers.id"), nullable=True)
    converted_contact_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("crm_contacts.id"), nullable=True)
    converted_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
