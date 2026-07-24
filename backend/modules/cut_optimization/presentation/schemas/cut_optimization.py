import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class PieceSpecIn(BaseModel):
    label: str
    length_mm: Decimal
    width_mm: Decimal
    quantity: int = 1
    allow_rotation: bool = True


class RunCutOptimizationCreate(BaseModel):
    pieces: List[PieceSpecIn]
    kerf_mm: Decimal = Decimal("3")
    slab_id: Optional[uuid.UUID] = None
    slab_length_mm: Optional[Decimal] = None
    slab_width_mm: Optional[Decimal] = None
    material_id: Optional[uuid.UUID] = None
    related_order_item_id: Optional[uuid.UUID] = None
    related_quote_item_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class PlacedPieceOut(BaseModel):
    label: str
    instance_index: int
    x_mm: Decimal
    y_mm: Decimal
    length_mm: Decimal
    width_mm: Decimal
    rotated: bool


class UnplacedPieceOut(BaseModel):
    label: str
    instance_index: int
    length_mm: Decimal
    width_mm: Decimal
    reason: str


class CutOptimizationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: Optional[uuid.UUID]
    slab_id: Optional[uuid.UUID]
    source: str
    slab_length_mm: Decimal
    slab_width_mm: Decimal
    kerf_mm: Decimal
    pieces: list
    placements: list
    unplaced: list
    total_area_m2: Decimal
    placed_area_m2: Decimal
    waste_area_m2: Decimal
    utilization_pct: Decimal
    notes: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime


class CutOptimizationRunListOut(BaseModel):
    items: List[CutOptimizationRunOut]
    next_cursor: Optional[str] = None


class RecommendOffcutsRequest(BaseModel):
    material_id: uuid.UUID
    pieces: List[PieceSpecIn]
    kerf_mm: Decimal = Decimal("3")
    thickness_mm: Optional[str] = None
    finish: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    persist_top_candidate: bool = True


class OffcutCandidateOut(BaseModel):
    slab_id: uuid.UUID
    slab_number: str
    warehouse_id: uuid.UUID
    slab_length_mm: Decimal
    slab_width_mm: Decimal
    fits: bool
    utilization_pct: Decimal
    waste_area_m2: Decimal
    total_area_m2: Decimal
    explanation: str
    placements: List[PlacedPieceOut]


class RecommendOffcutsResponseOut(BaseModel):
    candidates: List[OffcutCandidateOut]
    recommend_new_slab: bool
    reason: str
    persisted_run_id: Optional[uuid.UUID] = None


# ── Multi-slab / cross-job batch optimization (Phase 20) ─────────────────────


class RunBatchCutOptimizationCreate(BaseModel):
    material_id: uuid.UUID
    pieces: List[PieceSpecIn]
    kerf_mm: Decimal = Decimal("3")
    slab_ids: Optional[List[uuid.UUID]] = None
    thickness_mm: Optional[str] = None
    finish: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    max_slabs: int = 20
    notes: Optional[str] = None


class CutOptimizationBatchRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: Optional[uuid.UUID]
    kerf_mm: Decimal
    slabs: list
    pieces: list
    placements: list
    unplaced: list
    slabs_used_count: int
    total_area_m2: Decimal
    placed_area_m2: Decimal
    waste_area_m2: Decimal
    utilization_pct: Decimal
    notes: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime


class CutOptimizationBatchRunListOut(BaseModel):
    items: List[CutOptimizationBatchRunOut]
    next_cursor: Optional[str] = None
