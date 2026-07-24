from typing import Any, List, Optional

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class CutOptimizationBatchRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One persisted result of the multi-slab / cross-job batch nesting
    engine (Phase 20) -- a sibling to `CutOptimizationRun` (single slab),
    not an extension of it: a batch run's input/output shape is
    fundamentally plural (many slabs, many pieces, possibly many jobs),
    so overloading the singular `slab_id`/`slab_length_mm`/`slab_width_mm`
    columns on the existing table would have meant making them nullable in
    a way that breaks the single-slab History/detail pages' assumptions.
    Same "immutable JSON snapshot" philosophy as `CutOptimizationRun`
    otherwise: `slabs`/`pieces`/`placements`/`unplaced` are stored as JSON,
    not normalized, since a run is a point-in-time result, not a live
    entity queried piece-by-piece."""

    __tablename__ = "cut_optimization_batch_runs"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    material_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("catalog_materials.id"), nullable=True, index=True)

    kerf_mm: Mapped[Any] = mapped_column(Numeric(6, 2), nullable=False)

    # One entry per slab actually used: {slab_id, slab_ref, length_mm, width_mm}
    slabs: Mapped[List[Any]] = mapped_column(JSON, nullable=False)
    # The full requested piece pool: {label, length_mm, width_mm, quantity, allow_rotation}
    pieces: Mapped[List[Any]] = mapped_column(JSON, nullable=False)
    # One entry per placed piece, tagged with which slab it landed on:
    # {slab_ref, label, instance_index, x_mm, y_mm, length_mm, width_mm, rotated}
    placements: Mapped[List[Any]] = mapped_column(JSON, nullable=False)
    unplaced: Mapped[List[Any]] = mapped_column(JSON, nullable=False, default=list)

    slabs_used_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_area_m2: Mapped[Any] = mapped_column(Numeric(10, 3), nullable=False)
    placed_area_m2: Mapped[Any] = mapped_column(Numeric(10, 3), nullable=False)
    waste_area_m2: Mapped[Any] = mapped_column(Numeric(10, 3), nullable=False)
    utilization_pct: Mapped[Any] = mapped_column(Numeric(5, 2), nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
