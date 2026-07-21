from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class PurchaseOrderLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One ordered material line within a PurchaseOrder. `quantity_received`
    accumulates across every GoodsReceipt recorded against this line -- it
    never resets, and can never exceed `quantity` (enforced in the use case,
    not the DB)."""

    __tablename__ = "purchase_order_lines"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    purchase_order_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    material_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("catalog_materials.id"), nullable=True, index=True
    )

    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    quantity: Mapped[str] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    unit: Mapped[str] = mapped_column(String(10), nullable=False, default="unit")
    unit_cost: Mapped[str] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    line_total: Mapped[str] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    quantity_received: Mapped[str] = mapped_column(Numeric(10, 3), nullable=False, default=0)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
