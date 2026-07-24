"""Multi-slab / cross-job batch nesting (Phase 20: Advanced Cut Optimization
& Supply Chain Intelligence). Extends the single-slab `pack_pieces` engine
(`cutting_algorithm.py`, left completely unmodified -- it's reused here
unchanged as the inner per-slab packer) into an outer bin-packing
orchestrator: given an ordered list of candidate slabs and one combined
pool of pieces (which may span multiple jobs/work orders -- see the
`label` convention below), it fills slabs in the given order, carrying
whatever didn't fit on one slab forward to the next, until every piece is
placed or the slab list is exhausted.

Cross-job tracking is deliberately NOT a new field threaded through
`PieceSpec`/`PlacedPiece` (that would mean touching the single-slab engine
every other use case already depends on). Instead, by convention, a
caller nesting pieces from multiple jobs prefixes each piece's `label`
with its job identifier (e.g. "WO-1024: Countertop A") -- the label is
already free text everywhere else in this module (Optimization History,
the SVG visualization), so this reuses an existing extension point rather
than inventing a parallel one.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from modules.cut_optimization.domain.cutting_algorithm import (
    MM2_PER_M2,
    PieceSpec,
    PlacedPiece,
    UnplacedPiece,
    pack_pieces,
)


@dataclass
class SlabSpec:
    """One candidate bin for the batch packer. `ref` is a human-readable
    identifier (a real slab's `slab_number`, or a caller-assigned label for
    a hypothetical slab) -- `slab_id` is only set for a real Catalog slab,
    so a persisted batch run can still be traced back to real inventory
    without forcing every batch run to be against real stock."""

    ref: str
    length_mm: Decimal
    width_mm: Decimal
    slab_id: Optional[str] = None


@dataclass
class SlabUsageResult:
    slab: SlabSpec
    placements: List[PlacedPiece] = field(default_factory=list)
    placed_area_m2: Decimal = Decimal("0")
    waste_area_m2: Decimal = Decimal("0")
    utilization_pct: Decimal = Decimal("0")


@dataclass
class BatchPackResult:
    kerf_mm: Decimal
    slabs_used: List[SlabUsageResult] = field(default_factory=list)
    unplaced: List[UnplacedPiece] = field(default_factory=list)
    total_area_m2: Decimal = Decimal("0")
    placed_area_m2: Decimal = Decimal("0")
    waste_area_m2: Decimal = Decimal("0")
    utilization_pct: Decimal = Decimal("0")

    @property
    def all_placed(self) -> bool:
        return len(self.unplaced) == 0

    @property
    def slabs_used_count(self) -> int:
        return len(self.slabs_used)


def _rebuild_remaining(unplaced: List[UnplacedPiece], allow_rotation_by_label: dict) -> List[PieceSpec]:
    """Turns one slab's unplaced instances back into single-quantity
    PieceSpecs for the next slab attempt -- `pack_pieces` always expands by
    quantity internally, so re-expressing each leftover instance as its own
    quantity-1 spec keeps every subsequent `pack_pieces` call working on
    exactly the individual pieces still needing a home, not the original
    (now-too-large) quantities."""
    return [
        PieceSpec(
            label=u.label,
            length_mm=u.length_mm,
            width_mm=u.width_mm,
            quantity=1,
            allow_rotation=allow_rotation_by_label.get(u.label, True),
        )
        for u in unplaced
    ]


def pack_pieces_multi_slab(
    *, slabs: List[SlabSpec], kerf_mm: Decimal, pieces: List[PieceSpec]
) -> BatchPackResult:
    kerf_mm = Decimal(kerf_mm)
    result = BatchPackResult(kerf_mm=kerf_mm)

    allow_rotation_by_label = {p.label: p.allow_rotation for p in pieces}
    remaining = list(pieces)

    for slab_spec in slabs:
        if not remaining:
            break

        slab_length_mm = Decimal(slab_spec.length_mm)
        slab_width_mm = Decimal(slab_spec.width_mm)
        pack_result = pack_pieces(
            slab_length_mm=slab_length_mm, slab_width_mm=slab_width_mm, kerf_mm=kerf_mm, pieces=remaining
        )

        # A slab that placed nothing at all wasn't actually consumed by
        # this run -- skip counting it as "used" and try the next
        # candidate with the same remaining pool, rather than recording a
        # zero-yield slab as part of the result.
        if pack_result.placements:
            result.slabs_used.append(SlabUsageResult(
                slab=slab_spec,
                placements=pack_result.placements,
                placed_area_m2=pack_result.placed_area_m2,
                waste_area_m2=pack_result.waste_area_m2,
                utilization_pct=pack_result.utilization_pct,
            ))
            result.total_area_m2 += (slab_length_mm * slab_width_mm) / MM2_PER_M2
            result.placed_area_m2 += pack_result.placed_area_m2

        remaining = _rebuild_remaining(pack_result.unplaced, allow_rotation_by_label)

    result.unplaced = [
        UnplacedPiece(
            label=p.label, instance_index=1, length_mm=p.length_mm, width_mm=p.width_mm,
            reason="No remaining slab in this batch had room for this piece",
        )
        for p in remaining
    ]
    result.waste_area_m2 = result.total_area_m2 - result.placed_area_m2
    if result.total_area_m2 > 0:
        result.utilization_pct = (result.placed_area_m2 / result.total_area_m2 * Decimal("100")).quantize(Decimal("0.01"))
    return result
