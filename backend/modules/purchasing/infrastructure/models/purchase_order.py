from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.purchasing.domain.value_objects import DEFAULT_PURCHASE_ORDER_CURRENCY, PO_STATUS_DRAFT


class PurchaseOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A purchase order raised against a Supplier to restock Catalog materials."""

    __tablename__ = "purchase_orders"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False, index=True)

    po_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=PO_STATUS_DRAFT, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default=DEFAULT_PURCHASE_ORDER_CURRENCY)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_delivery_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    subtotal_amount: Mapped[str] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_amount: Mapped[str] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    cancelled_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unpaid", index=True)
    amount_paid: Mapped[str] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    payment_due_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    rfq_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("purchase_rfqs.id"), nullable=True, index=True)
