"""Smart Offcut Management (Phase 2 requirement #2): when building a
quotation or production order, search existing offcuts before
recommending a fresh slab purchase. Every candidate offcut is evaluated
by actually running the same nesting algorithm against it (not a blunt
dimension/area filter), ranked by how much of the requested piece(s) it
would use, and only surfaced as "recommend purchasing a new slab" once no
existing offcut can fit the requirement."""
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.infrastructure.models.slab import Slab
from modules.catalog.infrastructure.repositories.slab_repository import SlabRepository
from modules.cut_optimization.application.dtos import RecommendOffcutsInput
from modules.cut_optimization.domain import events as cut_optimization_events
from modules.cut_optimization.domain.cutting_algorithm import PieceSpec, PackResult, pack_pieces
from modules.cut_optimization.domain.exceptions import InvalidOptimizationInputError
from modules.cut_optimization.domain.value_objects import RUN_SOURCE_OFFCUT_RECOMMENDATION
from modules.cut_optimization.infrastructure.models.cut_optimization_run import CutOptimizationRun
from modules.cut_optimization.infrastructure.repositories.cut_optimization_run_repository import (
    CutOptimizationRunRepository,
)

MODULE = "cut_optimization"


@dataclass
class OffcutCandidateResult:
    slab: Slab
    pack_result: PackResult
    fits: bool
    explanation: str


@dataclass
class RecommendationOutput:
    candidates: List[OffcutCandidateResult]
    recommend_new_slab: bool
    reason: str
    persisted_run: Optional[CutOptimizationRun]


def _validate(data: RecommendOffcutsInput) -> None:
    if not data.pieces:
        raise InvalidOptimizationInputError("At least one piece is required")
    for piece in data.pieces:
        if piece.length_mm <= 0 or piece.width_mm <= 0:
            raise InvalidOptimizationInputError(f"Piece '{piece.label}' has a non-positive dimension")


class RecommendOffcutsUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.slabs = SlabRepository(db)
        self.runs = CutOptimizationRunRepository(db)

    def execute(self, data: RecommendOffcutsInput) -> RecommendationOutput:
        _validate(data)

        piece_specs = [
            PieceSpec(label=p.label, length_mm=p.length_mm, width_mm=p.width_mm,
                      quantity=p.quantity, allow_rotation=p.allow_rotation)
            for p in data.pieces
        ]

        candidates_raw = self.slabs.list_offcut_candidates(
            company_id=data.company_id,
            material_id=data.material_id,
            thickness_mm=data.thickness_mm,
            finish=data.finish,
            warehouse_id=data.warehouse_id,
        )

        evaluated: List[OffcutCandidateResult] = []
        for slab in candidates_raw:
            if slab.length_mm is None or slab.width_mm is None:
                continue
            pack_result = pack_pieces(
                slab_length_mm=slab.length_mm, slab_width_mm=slab.width_mm,
                kerf_mm=data.kerf_mm, pieces=piece_specs,
            )
            fits = pack_result.all_placed
            explanation = self._explain(slab, pack_result, fits)
            evaluated.append(OffcutCandidateResult(slab=slab, pack_result=pack_result, fits=fits, explanation=explanation))

        fitting = [c for c in evaluated if c.fits]
        # Rank by utilization descending (least waste first), tie-broken by
        # the smaller of the two candidate slabs -- using the smallest
        # offcut that does the job keeps larger remnants available for a
        # bigger job later, instead of "spending" them on something small.
        fitting.sort(key=lambda c: (-c.pack_result.utilization_pct, c.pack_result.total_area_m2))

        if not fitting:
            reason = (
                "No existing offcut in stock can fit the requested piece(s) "
                f"(evaluated {len(evaluated)} candidate offcut(s) matching material/thickness/finish)."
                if evaluated
                else "No offcuts in stock match this material/thickness/finish combination."
            )
            self._audit(data, outcome="no_suitable_offcut", candidate_count=len(evaluated))
            return RecommendationOutput(candidates=evaluated, recommend_new_slab=True, reason=reason, persisted_run=None)

        persisted_run = None
        if data.persist_top_candidate:
            persisted_run = self._persist_winner(data, fitting[0], piece_specs)

        self._audit(data, outcome="offcut_recommended", candidate_count=len(evaluated))
        return RecommendationOutput(
            candidates=fitting + [c for c in evaluated if not c.fits],
            recommend_new_slab=False,
            reason=f"{len(fitting)} matching offcut(s) can fit the requested piece(s); showing the best fit first.",
            persisted_run=persisted_run,
        )

    def _explain(self, slab: Slab, pack_result: PackResult, fits: bool) -> str:
        if not fits:
            unplaced_labels = ", ".join(sorted({u.label for u in pack_result.unplaced}))
            return f"Doesn't fit: {unplaced_labels} would not fit on this {slab.slab_number} remnant."
        return (
            f"Selected {slab.slab_number}: fits all requested pieces at "
            f"{pack_result.utilization_pct}% utilization "
            f"({pack_result.waste_area_m2} m² waste out of {pack_result.total_area_m2} m² available)."
        )

    def _persist_winner(self, data: RecommendOffcutsInput, winner: OffcutCandidateResult, piece_specs) -> CutOptimizationRun:
        run = CutOptimizationRun(
            company_id=data.company_id,
            material_id=data.material_id,
            slab_id=winner.slab.id,
            source=RUN_SOURCE_OFFCUT_RECOMMENDATION,
            slab_length_mm=winner.slab.length_mm,
            slab_width_mm=winner.slab.width_mm,
            kerf_mm=data.kerf_mm,
            pieces=[
                {"label": p.label, "length_mm": str(p.length_mm), "width_mm": str(p.width_mm),
                 "quantity": p.quantity, "allow_rotation": p.allow_rotation}
                for p in data.pieces
            ],
            placements=[
                {"label": pl.label, "instance_index": pl.instance_index, "x_mm": str(pl.x_mm), "y_mm": str(pl.y_mm),
                 "length_mm": str(pl.length_mm), "width_mm": str(pl.width_mm), "rotated": pl.rotated}
                for pl in winner.pack_result.placements
            ],
            unplaced=[],
            total_area_m2=winner.pack_result.total_area_m2,
            placed_area_m2=winner.pack_result.placed_area_m2,
            waste_area_m2=winner.pack_result.waste_area_m2,
            utilization_pct=winner.pack_result.utilization_pct,
            notes=winner.explanation,
            created_by=data.actor_user_id,
        )
        self.runs.add(run)
        self.db.flush()
        event_bus.publish(
            Event(
                name=cut_optimization_events.OFFCUT_RECOMMENDATION_COMPUTED,
                company_id=data.company_id,
                payload={"run_id": str(run.id), "slab_id": str(winner.slab.id), "utilization_pct": str(winner.pack_result.utilization_pct)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return run

    def _audit(self, data: RecommendOffcutsInput, *, outcome: str, candidate_count: int) -> None:
        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="offcut_recommendation.computed",
            entity_type="cut_optimization_recommendation",
            entity_id=data.material_id,
            diff={"outcome": outcome, "candidate_count": candidate_count},
        )
        self.db.flush()
