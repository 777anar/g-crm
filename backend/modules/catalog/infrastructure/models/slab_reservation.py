from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.catalog.domain.value_objects import RESERVATION_STATUS_ACTIVE


class SlabReservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The durable record of "this slab is allocated to this order item" --
    richer than Slab.status alone, which only tells you a slab *is*
    reserved, never for whom. `order_id`/`order_item_id` are plain,
    unconstrained UUID columns rather than real foreign keys (the same
    "polymorphic reference, application-layer only" pattern already used by
    `documents.related_entity_id` and `crm_leads.campaign_id`) so Catalog,
    which every other module depends on, never has to depend on Orders."""

    __tablename__ = "catalog_slab_reservations"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    slab_id: Mapped[str] = mapped_column(GUID(), ForeignKey("catalog_slabs.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    order_item_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RESERVATION_STATUS_ACTIVE, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reserved_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    reserved_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
