"""Run Cut Optimization: the direct, manual entry point to the nesting
algorithm (Phase 2 requirement #1) -- either against a specific Catalog
slab (existing stock or an offcut) or against raw hypothetical
dimensions ("if I bought a 3200x1600 slab, how many of these would fit?").
Every run is persisted as Optimization History (requirement #4)."""
import uuid

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.infrastructure.repositories.slab_repository import SlabRepository
from modules.cut_optimization.application.dtos import RunCutOptimizationInput
from modules.cut_optimization.domain import events as cut_optimization_events
from modules.cut_optimization.domain.cutting_algorithm import PieceSpec, pack_pieces
from modules.cut_optimization.domain.exceptions import InvalidOptimizationInputError, NoSlabDimensionsProvidedError
from modules.cut_optimization.domain.value_objects import RUN_SOURCE_MANUAL
from modules.cut_optimization.infrastructure.models.cut_optimization_run import CutOptimizationRun
from modules.cut_optimization.infrastructure.repositories.cut_optimization_run_repository import (
    CutOptimizationRunRepository,
)

MODULE = "cut_optimization"


def resolve_slab_dimensions(db: Session, data: RunCutOptimizationInput):
    """Shared by both use cases in this module: a slab_id always wins
    (the real, physical piece of stone), explicit dimensions are the
    what-if fallback for a slab that doesn't exist in inventory yet."""
    if data.slab_id is not None:
        slab = SlabRepository(db).get(company_id=data.company_id, slab_id=data.slab_id)
        if slab is None:
            raise NotFoundError("Slab not found")
        if slab.length_mm is None or slab.width_mm is None:
            raise InvalidOptimizationInputError("This slab has no recorded length_mm/width_mm to optimize against")
        return slab.length_mm, slab.width_mm, slab.material_id

    if data.slab_length_mm is None or data.slab_width_mm is None:
        raise NoSlabDimensionsProvidedError(
            "Provide either slab_id or both slab_length_mm and slab_width_mm"
        )
    return data.slab_length_mm, data.slab_width_mm, data.material_id


def _validate_pieces(data) -> None:
    if not data.pieces:
        raise InvalidOptimizationInputError("At least one piece is required")
    for piece in data.pieces:
        if piece.length_mm <= 0 or piece.width_mm <= 0:
            raise InvalidOptimizationInputError(f"Piece '{piece.label}' has a non-positive dimension")
        if piece.quantity < 1:
            raise InvalidOptimizationInputError(f"Piece '{piece.label}' must have quantity >= 1")
    if data.kerf_mm < 0:
        raise InvalidOptimizationInputError("kerf_mm cannot be negative")


class RunCutOptimizationUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.runs = CutOptimizationRunRepository(db)

    def execute(self, data: RunCutOptimizationInput) -> CutOptimizationRun:
        _validate_pieces(data)
        slab_length_mm, slab_width_mm, resolved_material_id = resolve_slab_dimensions(self.db, data)

        result = pack_pieces(
            slab_length_mm=slab_length_mm,
            slab_width_mm=slab_width_mm,
            kerf_mm=data.kerf_mm,
            pieces=[
                PieceSpec(
                    label=p.label, length_mm=p.length_mm, width_mm=p.width_mm,
                    quantity=p.quantity, allow_rotation=p.allow_rotation,
                )
                for p in data.pieces
            ],
        )

        run = CutOptimizationRun(
            company_id=data.company_id,
            material_id=data.material_id or resolved_material_id,
            slab_id=data.slab_id,
            source=RUN_SOURCE_MANUAL,
            slab_length_mm=slab_length_mm,
            slab_width_mm=slab_width_mm,
            kerf_mm=data.kerf_mm,
            pieces=[
                {"label": p.label, "length_mm": str(p.length_mm), "width_mm": str(p.width_mm),
                 "quantity": p.quantity, "allow_rotation": p.allow_rotation}
                for p in data.pieces
            ],
            placements=[
                {"label": pl.label, "instance_index": pl.instance_index, "x_mm": str(pl.x_mm), "y_mm": str(pl.y_mm),
                 "length_mm": str(pl.length_mm), "width_mm": str(pl.width_mm), "rotated": pl.rotated}
                for pl in result.placements
            ],
            unplaced=[
                {"label": u.label, "instance_index": u.instance_index, "length_mm": str(u.length_mm),
                 "width_mm": str(u.width_mm), "reason": u.reason}
                for u in result.unplaced
            ],
            total_area_m2=result.total_area_m2,
            placed_area_m2=result.placed_area_m2,
            waste_area_m2=result.waste_area_m2,
            utilization_pct=result.utilization_pct,
            related_order_item_id=data.related_order_item_id,
            related_quote_item_id=data.related_quote_item_id,
            notes=data.notes,
            created_by=data.actor_user_id,
        )
        self.runs.add(run)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="cut_optimization_run.created",
            entity_type="cut_optimization_run",
            entity_id=run.id,
            diff={
                "slab_id": str(data.slab_id) if data.slab_id else None,
                "utilization_pct": str(result.utilization_pct),
                "piece_count": sum(p.quantity for p in data.pieces),
            },
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=cut_optimization_events.CUT_OPTIMIZATION_RUN_CREATED,
                company_id=data.company_id,
                payload={"run_id": str(run.id), "utilization_pct": str(result.utilization_pct)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return run
