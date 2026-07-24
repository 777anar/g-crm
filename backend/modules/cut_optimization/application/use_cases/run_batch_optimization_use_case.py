"""Multi-slab / cross-job batch optimization (Phase 20: Advanced Cut
Optimization & Supply Chain Intelligence). Takes the single-slab engine
Version 2.35.0 shipped and turns it into a real production-run planning
tool: nest every piece from however many jobs were combined into one
request across as many slabs/offcuts as it takes, preferring the
company's existing (smaller) offcut inventory before consuming full
slabs -- the same "use up what's already in stock first" philosophy
Smart Offcut Management already applies to a single job, extended to a
whole run's worth of jobs at once."""
from typing import List

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.infrastructure.models.slab import Slab
from modules.catalog.infrastructure.repositories.slab_repository import SlabRepository
from modules.cut_optimization.application.dtos import RunBatchCutOptimizationInput
from modules.cut_optimization.domain import events as cut_optimization_events
from modules.cut_optimization.domain.batch_cutting_algorithm import SlabSpec, pack_pieces_multi_slab
from modules.cut_optimization.domain.cutting_algorithm import PieceSpec
from modules.cut_optimization.domain.exceptions import InvalidOptimizationInputError, NoSlabsAvailableError
from modules.cut_optimization.infrastructure.models.cut_optimization_batch_run import CutOptimizationBatchRun
from modules.cut_optimization.infrastructure.repositories.cut_optimization_batch_run_repository import (
    CutOptimizationBatchRunRepository,
)

MODULE = "cut_optimization"


def _validate(data: RunBatchCutOptimizationInput) -> None:
    if not data.pieces:
        raise InvalidOptimizationInputError("At least one piece is required")
    for piece in data.pieces:
        if piece.length_mm <= 0 or piece.width_mm <= 0:
            raise InvalidOptimizationInputError(f"Piece '{piece.label}' has a non-positive dimension")
        if piece.quantity < 1:
            raise InvalidOptimizationInputError(f"Piece '{piece.label}' must have quantity >= 1")
    if data.kerf_mm < 0:
        raise InvalidOptimizationInputError("kerf_mm cannot be negative")
    if data.max_slabs < 1:
        raise InvalidOptimizationInputError("max_slabs must be at least 1")


class RunBatchCutOptimizationUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.slabs = SlabRepository(db)
        self.runs = CutOptimizationBatchRunRepository(db)

    def execute(self, data: RunBatchCutOptimizationInput) -> CutOptimizationBatchRun:
        _validate(data)
        candidate_slabs = self._resolve_candidate_slabs(data)
        if not candidate_slabs:
            raise NoSlabsAvailableError(
                "No available slabs or offcuts matched this request -- pass slab_ids explicitly, or "
                "relax the thickness/finish/warehouse filters"
            )

        piece_specs = [
            PieceSpec(label=p.label, length_mm=p.length_mm, width_mm=p.width_mm,
                      quantity=p.quantity, allow_rotation=p.allow_rotation)
            for p in data.pieces
        ]
        slab_specs = [
            SlabSpec(ref=slab.slab_number, length_mm=slab.length_mm, width_mm=slab.width_mm, slab_id=str(slab.id))
            for slab in candidate_slabs
        ]

        result = pack_pieces_multi_slab(slabs=slab_specs, kerf_mm=data.kerf_mm, pieces=piece_specs)

        run = CutOptimizationBatchRun(
            company_id=data.company_id,
            material_id=data.material_id,
            kerf_mm=data.kerf_mm,
            slabs=[
                {
                    "slab_id": usage.slab.slab_id, "slab_ref": usage.slab.ref,
                    "length_mm": str(usage.slab.length_mm), "width_mm": str(usage.slab.width_mm),
                }
                for usage in result.slabs_used
            ],
            pieces=[
                {"label": p.label, "length_mm": str(p.length_mm), "width_mm": str(p.width_mm),
                 "quantity": p.quantity, "allow_rotation": p.allow_rotation}
                for p in data.pieces
            ],
            placements=[
                {
                    "slab_ref": usage.slab.ref, "label": pl.label, "instance_index": pl.instance_index,
                    "x_mm": str(pl.x_mm), "y_mm": str(pl.y_mm),
                    "length_mm": str(pl.length_mm), "width_mm": str(pl.width_mm), "rotated": pl.rotated,
                }
                for usage in result.slabs_used
                for pl in usage.placements
            ],
            unplaced=[
                {"label": u.label, "instance_index": u.instance_index, "length_mm": str(u.length_mm),
                 "width_mm": str(u.width_mm), "reason": u.reason}
                for u in result.unplaced
            ],
            slabs_used_count=result.slabs_used_count,
            total_area_m2=result.total_area_m2,
            placed_area_m2=result.placed_area_m2,
            waste_area_m2=result.waste_area_m2,
            utilization_pct=result.utilization_pct,
            notes=data.notes,
            created_by=data.actor_user_id,
        )
        self.runs.add(run)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="cut_optimization_batch_run.created",
            entity_type="cut_optimization_batch_run",
            entity_id=run.id,
            diff={
                "material_id": str(data.material_id),
                "slabs_used_count": result.slabs_used_count,
                "utilization_pct": str(result.utilization_pct),
                "piece_count": sum(p.quantity for p in data.pieces),
                "unplaced_count": len(result.unplaced),
            },
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=cut_optimization_events.CUT_OPTIMIZATION_BATCH_RUN_CREATED,
                company_id=data.company_id,
                payload={
                    "batch_run_id": str(run.id),
                    "slabs_used_count": result.slabs_used_count,
                    "utilization_pct": str(result.utilization_pct),
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return run

    def _resolve_candidate_slabs(self, data: RunBatchCutOptimizationInput) -> List[Slab]:
        if data.slab_ids:
            slabs = []
            for slab_id in data.slab_ids:
                slab = self.slabs.get(company_id=data.company_id, slab_id=slab_id)
                if slab is None:
                    raise NotFoundError(f"Slab {slab_id} not found")
                if slab.length_mm is None or slab.width_mm is None:
                    raise InvalidOptimizationInputError(
                        f"Slab '{slab.slab_number}' has no recorded length_mm/width_mm to optimize against"
                    )
                slabs.append(slab)
            return slabs

        # Auto-select: every available slab (fresh stock and offcuts alike)
        # for this material, smallest-area first -- the same "spend the
        # smallest usable piece of inventory first" preference Smart
        # Offcut Management already applies, extended here across however
        # many slabs the whole batch ends up needing.
        return self.slabs.list_available_for_material(
            company_id=data.company_id,
            material_id=data.material_id,
            thickness_mm=data.thickness_mm,
            finish=data.finish,
            warehouse_id=data.warehouse_id,
            limit=data.max_slabs,
        )
