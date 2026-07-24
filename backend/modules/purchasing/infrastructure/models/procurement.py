from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class SupplierContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_contacts"
    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[Optional[str]] = mapped_column(String(120))
    email: Mapped[Optional[str]] = mapped_column(String(320))
    phone: Mapped[Optional[str]] = mapped_column(String(80))
    is_primary: Mapped[bool] = mapped_column(nullable=False, default=False)


class PurchaseRFQ(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_rfqs"
    __table_args__ = (UniqueConstraint("company_id", "rfq_number", name="uq_purchase_rfq_number"),)
    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False, index=True)
    rfq_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AZN")
    response_due_date: Mapped[Optional[str]] = mapped_column(String(10))
    quoted_total: Mapped[Optional[str]] = mapped_column(Numeric(14, 2))
    supplier_reference: Mapped[Optional[str]] = mapped_column(String(120))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)


class PurchaseRFQLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_rfq_lines"
    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    rfq_id: Mapped[str] = mapped_column(GUID(), ForeignKey("purchase_rfqs.id"), nullable=False, index=True)
    material_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[str] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="unit")
    quoted_unit_cost: Mapped[Optional[str]] = mapped_column(Numeric(14, 2))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PurchaseReturn(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_returns"
    __table_args__ = (UniqueConstraint("company_id", "return_number", name="uq_purchase_return_number"),)
    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False, index=True)
    purchase_order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("purchase_orders.id"), nullable=False, index=True)
    return_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[str] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    completed_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"))
    completed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True))


class PurchaseReturnLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_return_lines"
    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    purchase_return_id: Mapped[str] = mapped_column(GUID(), ForeignKey("purchase_returns.id"), nullable=False, index=True)
    goods_receipt_id: Mapped[str] = mapped_column(GUID(), ForeignKey("goods_receipts.id"), nullable=False, index=True)
    quantity: Mapped[str] = mapped_column(Numeric(10, 3), nullable=False)
    unit_cost: Mapped[str] = mapped_column(Numeric(14, 2), nullable=False)
    line_total: Mapped[str] = mapped_column(Numeric(14, 2), nullable=False)


class PurchaseAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_attachments"
    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(GUID(), ForeignKey("documents.id"), nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    added_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
