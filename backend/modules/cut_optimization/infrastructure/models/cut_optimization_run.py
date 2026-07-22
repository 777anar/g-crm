from typing import Any, List, Optional

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.cut_optimization.domain.value_objects import RUN_SOURCE_MANUAL


class CutOptimizationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One persisted result of the slab-cutting nesting algorithm --
    Optimization History (Phase 2 requirement #4). Deliberately stores the
    full input (pieces) and full output (placements/unplaced) as JSON
    rather than normalized child tables: a run is an immutable snapshot of
    "what the algorithm computed at this moment," not a live entity that
    gets queried piece-by-piece, so there is no normalization benefit,
    only round-trip simplicity for "reopen this exact layout" (requirement
    #4's other half)."""

    __tablename__ = "cut_optimization_runs"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    material_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=True, index=True)
    slab_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_slabs.id"), nullable=True, index=True)

    source: Mapped[str] = mapped_column(String(30), nullable=False, default=RUN_SOURCE_MANUAL, index=True)

    slab_length_mm: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    slab_width_mm: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    kerf_mm: Mapped[Any] = mapped_column(Numeric(6, 2), nullable=False)

    pieces: Mapped[List[Any]] = mapped_column(JSON, nullable=False)
    placements: Mapped[List[Any]] = mapped_column(JSON, nullable=False)
    unplaced: Mapped[List[Any]] = mapped_column(JSON, nullable=False, default=list)

    total_area_m2: Mapped[Any] = mapped_column(Numeric(10, 3), nullable=False)
    placed_area_m2: Mapped[Any] = mapped_column(Numeric(10, 3), nullable=False)
    waste_area_m2: Mapped[Any] = mapped_column(Numeric(10, 3), nullable=False)
    utilization_pct: Mapped[Any] = mapped_column(Numeric(5, 2), nullable=False)

    # Polymorphic reference, application-layer only -- same pattern as
    # catalog_slab_reservations.order_id (Phase 1): lets a run be traced
    # back to the quote/order item that triggered it without Cut
    # Optimization ever having to depend on Sales or Orders.
    related_order_item_id: Mapped[Optional[str]] = mapped_column(GUID(), nullable=True, index=True)
    related_quote_item_id: Mapped[Optional[str]] = mapped_column(GUID(), nullable=True, index=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
