import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.cut_optimization.application.dtos import PieceSpecInput, RecommendOffcutsInput, RunCutOptimizationInput
from modules.cut_optimization.application.use_cases import RecommendOffcutsUseCase, RunCutOptimizationUseCase
from modules.cut_optimization.domain.exceptions import CutOptimizationDomainError
from modules.cut_optimization.infrastructure.repositories.cut_optimization_run_repository import (
    CutOptimizationRunRepository,
)
from modules.cut_optimization.presentation.schemas.cut_optimization import (
    CutOptimizationRunListOut,
    CutOptimizationRunOut,
    OffcutCandidateOut,
    PlacedPieceOut,
    RecommendOffcutsRequest,
    RecommendOffcutsResponseOut,
    RunCutOptimizationCreate,
)

router = APIRouter()

_DOMAIN_ERRORS = (CutOptimizationDomainError,)


def _to_piece_inputs(pieces) -> list:
    return [
        PieceSpecInput(label=p.label, length_mm=p.length_mm, width_mm=p.width_mm,
                       quantity=p.quantity, allow_rotation=p.allow_rotation)
        for p in pieces
    ]


@router.post("/runs", response_model=CutOptimizationRunOut)
def run_cut_optimization(
    payload: RunCutOptimizationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cut_optimization:write")),
) -> CutOptimizationRunOut:
    use_case = RunCutOptimizationUseCase(db)
    try:
        run = use_case.execute(
            RunCutOptimizationInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                pieces=_to_piece_inputs(payload.pieces),
                kerf_mm=payload.kerf_mm,
                slab_id=payload.slab_id,
                slab_length_mm=payload.slab_length_mm,
                slab_width_mm=payload.slab_width_mm,
                material_id=payload.material_id,
                related_order_item_id=payload.related_order_item_id,
                related_quote_item_id=payload.related_quote_item_id,
                notes=payload.notes,
            )
        )
    except _DOMAIN_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(run)
    return CutOptimizationRunOut.model_validate(run)


@router.get("/runs", response_model=CutOptimizationRunListOut)
def list_cut_optimization_runs(
    material_id: Optional[uuid.UUID] = Query(default=None),
    slab_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cut_optimization:read")),
) -> CutOptimizationRunListOut:
    repo = CutOptimizationRunRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        material_id=material_id,
        slab_id=slab_id,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return CutOptimizationRunListOut(
        items=[CutOptimizationRunOut.model_validate(r) for r in page], next_cursor=next_cursor
    )


@router.get("/runs/{run_id}", response_model=CutOptimizationRunOut)
def get_cut_optimization_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cut_optimization:read")),
) -> CutOptimizationRunOut:
    """Reopening a previous layout (Phase 2 requirement #4) is just
    fetching its stored result -- the run is an immutable snapshot, so
    there is nothing to recompute."""
    run = CutOptimizationRunRepository(db).get(company_id=current_user.active_company_id, run_id=run_id)
    if run is None:
        raise NotFoundError("Optimization run not found")
    return CutOptimizationRunOut.model_validate(run)


@router.post("/recommendations", response_model=RecommendOffcutsResponseOut)
def recommend_offcuts(
    payload: RecommendOffcutsRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cut_optimization:read")),
) -> RecommendOffcutsResponseOut:
    use_case = RecommendOffcutsUseCase(db)
    try:
        output = use_case.execute(
            RecommendOffcutsInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                material_id=payload.material_id,
                pieces=_to_piece_inputs(payload.pieces),
                kerf_mm=payload.kerf_mm,
                thickness_mm=payload.thickness_mm,
                finish=payload.finish,
                warehouse_id=payload.warehouse_id,
                persist_top_candidate=payload.persist_top_candidate,
            )
        )
    except _DOMAIN_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()

    return RecommendOffcutsResponseOut(
        candidates=[
            OffcutCandidateOut(
                slab_id=c.slab.id,
                slab_number=c.slab.slab_number,
                warehouse_id=c.slab.warehouse_id,
                slab_length_mm=c.slab.length_mm,
                slab_width_mm=c.slab.width_mm,
                fits=c.fits,
                utilization_pct=c.pack_result.utilization_pct,
                waste_area_m2=c.pack_result.waste_area_m2,
                total_area_m2=c.pack_result.total_area_m2,
                explanation=c.explanation,
                placements=[
                    PlacedPieceOut(
                        label=pl.label, instance_index=pl.instance_index, x_mm=pl.x_mm, y_mm=pl.y_mm,
                        length_mm=pl.length_mm, width_mm=pl.width_mm, rotated=pl.rotated,
                    )
                    for pl in c.pack_result.placements
                ],
            )
            for c in output.candidates
        ],
        recommend_new_slab=output.recommend_new_slab,
        reason=output.reason,
        persisted_run_id=output.persisted_run.id if output.persisted_run else None,
    )
