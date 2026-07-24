"""Application-layer input DTOs. Presentation schemas (Pydantic) map onto
these before calling a use-case, keeping the use-case layer free of any
FastAPI/Pydantic import -- same pattern as modules/crm and modules/catalog."""
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class PieceSpecInput:
    label: str
    length_mm: Decimal
    width_mm: Decimal
    quantity: int = 1
    allow_rotation: bool = True


@dataclass
class RunCutOptimizationInput(ActorContext):
    pieces: List[PieceSpecInput] = field(default_factory=list)
    kerf_mm: Decimal = Decimal("3")
    slab_id: Optional[uuid.UUID] = None
    slab_length_mm: Optional[Decimal] = None
    slab_width_mm: Optional[Decimal] = None
    material_id: Optional[uuid.UUID] = None
    related_order_item_id: Optional[uuid.UUID] = None
    related_quote_item_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


@dataclass
class RecommendOffcutsInput(ActorContext):
    material_id: uuid.UUID
    pieces: List[PieceSpecInput] = field(default_factory=list)
    kerf_mm: Decimal = Decimal("3")
    thickness_mm: Optional[str] = None
    finish: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    persist_top_candidate: bool = True


@dataclass
class RunBatchCutOptimizationInput(ActorContext):
    """Multi-slab / cross-job batch optimization (Phase 20). `pieces` is
    one combined pool -- pieces from multiple jobs/work orders are simply
    concatenated into this one list, distinguished only by their `label`
    (see batch_cutting_algorithm.py's module docstring for the "prefix the
    label with a job identifier" convention this relies on)."""
    material_id: uuid.UUID
    pieces: List[PieceSpecInput] = field(default_factory=list)
    kerf_mm: Decimal = Decimal("3")
    slab_ids: Optional[List[uuid.UUID]] = None
    thickness_mm: Optional[str] = None
    finish: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    max_slabs: int = 20
    notes: Optional[str] = None
