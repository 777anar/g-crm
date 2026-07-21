from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class GoodsReceipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One receiving action recorded against a PurchaseOrderLine. When the
    line references a Catalog material and the receiver supplies slab
    details, `slab_id` points at the real `catalog_slabs` row this receipt
    created -- the inverse of Production's slab-consumption flow."""

    __tablename__ = "goods_receipts"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    purchase_order_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    purchase_order_line_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("purchase_order_lines.id"), nullable=False, index=True
    )
    slab_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_slabs.id"), nullable=True, index=True)

    quantity_received: Mapped[str] = mapped_column(Numeric(10, 3), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    received_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    received_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
