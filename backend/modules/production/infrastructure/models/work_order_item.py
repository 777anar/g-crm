from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class WorkOrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links one Order item (that references a specific slab) to the Work
    Order fabricating it. One row per slab consumed."""

    __tablename__ = "work_order_items"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("work_orders.id"), nullable=False, index=True)
    order_item_id: Mapped[str] = mapped_column(GUID(), ForeignKey("order_items.id"), nullable=False, index=True, unique=True)
    slab_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_slabs.id"), nullable=False, index=True)
