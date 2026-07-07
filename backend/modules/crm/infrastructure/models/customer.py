from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.crm.domain.value_objects import DEFAULT_CUSTOMER_STATUS


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

    # Stone-industry customer fields (Phase 3 / G-STONE GALLERY customization).
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    instagram: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    facebook: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_CUSTOMER_STATUS, index=True)

    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    deleted_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Every list/filter query scopes by company_id first, then (optionally)
    # by status or lead_source (see CustomerRepository.list) -- composite
    # indexes so that filter doesn't degrade to a per-company scan once a
    # company has thousands of customers (RELEASE_CHECKLIST.md M6).
    __table_args__ = (
        Index("ix_crm_customers_company_status", "company_id", "status"),
        Index("ix_crm_customers_company_lead_source", "company_id", "lead_source"),
    )
