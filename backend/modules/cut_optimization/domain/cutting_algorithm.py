"""The slab-cutting nesting algorithm -- pure domain logic, no framework or
DB dependency, per Clean Architecture. This is a domain *service* rather
than an entity: it's a stateless computation over value objects, not
something with its own identity or lifecycle.

Algorithm: shelf (guillotine) packing with best-fit-decreasing-area piece
ordering. Chosen deliberately over a full free-form nesting solver --
stone fabrication saws make straight guillotine cuts across a slab, not
arbitrary polygon nesting, so a shelf packer models the real cutting
process, not just an abstract rectangle-packing puzzle. Pieces are placed
largest-area-first (a well-established heuristic for this class of
problem: placing big pieces first leaves more usable room for the many
smaller pieces that follow than placing them in input order would).

Coordinate system: x runs along the slab's length (0..slab_length_mm), y
runs along its width (0..slab_width_mm), origin at the top-left corner of
the slab. A "shelf" is one horizontal row of pieces sharing the same y
range; shelves stack top-to-bottom. `kerf_mm` (the blade's cut width) is
subtracted as a gap between adjacent pieces in a shelf and between
adjacent shelves -- it is real material lost to the saw blade, so it
counts as waste, not usable area, exactly like an actual cut does.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

MM2_PER_M2 = Decimal("1000000")


@dataclass
class PieceSpec:
    label: str
    length_mm: Decimal
    width_mm: Decimal
    quantity: int = 1
    allow_rotation: bool = True


@dataclass
class PlacedPiece:
    label: str
    instance_index: int
    x_mm: Decimal
    y_mm: Decimal
    length_mm: Decimal
    width_mm: Decimal
    rotated: bool


@dataclass
class UnplacedPiece:
    label: str
    instance_index: int
    length_mm: Decimal
    width_mm: Decimal
    reason: str


@dataclass
class PackResult:
    slab_length_mm: Decimal
    slab_width_mm: Decimal
    kerf_mm: Decimal
    placements: List[PlacedPiece] = field(default_factory=list)
    unplaced: List[UnplacedPiece] = field(default_factory=list)
    total_area_m2: Decimal = Decimal("0")
    placed_area_m2: Decimal = Decimal("0")
    waste_area_m2: Decimal = Decimal("0")
    utilization_pct: Decimal = Decimal("0")

    @property
    def all_placed(self) -> bool:
        return len(self.unplaced) == 0


class _Shelf:
    __slots__ = ("y_start", "height", "cursor_x", "remaining_width")

    def __init__(self, y_start: Decimal, height: Decimal, width: Decimal):
        self.y_start = y_start
        self.height = height
        self.cursor_x = Decimal("0")
        self.remaining_width = width


def _expand_instances(pieces: List[PieceSpec]):
    """One entry per physical piece requested, not per PieceSpec row --
    a quantity of 5 becomes 5 individually-placed instances."""
    instances = []
    for piece in pieces:
        for i in range(piece.quantity):
            instances.append((piece, i + 1))
    return instances


def pack_pieces(*, slab_length_mm: Decimal, slab_width_mm: Decimal, kerf_mm: Decimal, pieces: List[PieceSpec]) -> PackResult:
    slab_length_mm = Decimal(slab_length_mm)
    slab_width_mm = Decimal(slab_width_mm)
    kerf_mm = Decimal(kerf_mm)

    result = PackResult(slab_length_mm=slab_length_mm, slab_width_mm=slab_width_mm, kerf_mm=kerf_mm)
    result.total_area_m2 = (slab_length_mm * slab_width_mm) / MM2_PER_M2

    # Largest-area-first: the standard "best fit decreasing" ordering for
    # shelf/guillotine packing -- placing big pieces before small ones
    # consistently yields less wasted area than input order or smallest-first.
    instances = _expand_instances(pieces)
    instances.sort(key=lambda pair: pair[0].length_mm * pair[0].width_mm, reverse=True)

    shelves: List[_Shelf] = []
    cursor_y = Decimal("0")
    placed_area = Decimal("0")

    for piece, instance_index in instances:
        orientations = [(piece.length_mm, piece.width_mm, False)]
        if piece.allow_rotation and piece.width_mm != piece.length_mm:
            orientations.append((piece.width_mm, piece.length_mm, True))

        # A piece that doesn't fit the slab in ANY allowed orientation can
        # never be placed, regardless of what's already on the slab --
        # reject it immediately with a clear reason.
        fits_slab_at_all = any(
            w <= slab_length_mm and h <= slab_width_mm for w, h, _ in orientations
        )
        if not fits_slab_at_all:
            result.unplaced.append(UnplacedPiece(
                label=piece.label, instance_index=instance_index,
                length_mm=piece.length_mm, width_mm=piece.width_mm,
                reason="Piece exceeds the slab's dimensions in every allowed orientation",
            ))
            continue

        placement = _place_in_best_shelf(shelves, orientations, kerf_mm)
        if placement is None:
            placement = _open_new_shelf(shelves, orientations, kerf_mm, cursor_y, slab_length_mm, slab_width_mm)

        if placement is None:
            result.unplaced.append(UnplacedPiece(
                label=piece.label, instance_index=instance_index,
                length_mm=piece.length_mm, width_mm=piece.width_mm,
                reason="No remaining space on the slab fits this piece",
            ))
            continue

        x, y, w, h, rotated, is_new_shelf = placement
        if is_new_shelf:
            cursor_y = y + h

        result.placements.append(PlacedPiece(
            label=piece.label, instance_index=instance_index,
            x_mm=x, y_mm=y, length_mm=w, width_mm=h, rotated=rotated,
        ))
        placed_area += (w * h) / MM2_PER_M2

    result.placed_area_m2 = placed_area
    result.waste_area_m2 = result.total_area_m2 - placed_area
    if result.total_area_m2 > 0:
        result.utilization_pct = (placed_area / result.total_area_m2 * Decimal("100")).quantize(Decimal("0.01"))
    return result


def _place_in_best_shelf(shelves: List[_Shelf], orientations, kerf_mm: Decimal) -> Optional[tuple]:
    """Best-fit: among every existing shelf + orientation combination the
    piece fits in, pick the one that leaves the least leftover width --
    the standard best-fit-decreasing tie-break, minimizing fragmentation
    for the smaller pieces still to come."""
    best = None
    best_leftover = None
    for shelf in shelves:
        for w, h, rotated in orientations:
            needed_width = w + (kerf_mm if shelf.cursor_x > 0 else Decimal("0"))
            if h <= shelf.height and needed_width <= shelf.remaining_width:
                leftover = shelf.remaining_width - needed_width
                if best_leftover is None or leftover < best_leftover:
                    best_leftover = leftover
                    best = (shelf, w, h, rotated, needed_width)

    if best is None:
        return None

    shelf, w, h, rotated, needed_width = best
    gap = needed_width - w
    x = shelf.cursor_x + gap
    y = shelf.y_start
    shelf.cursor_x = x + w
    shelf.remaining_width -= needed_width
    return x, y, w, h, rotated, False


def _open_new_shelf(shelves, orientations, kerf_mm: Decimal, cursor_y: Decimal, slab_length_mm: Decimal, slab_width_mm: Decimal) -> Optional[tuple]:
    gap_above = kerf_mm if shelves else Decimal("0")
    # Prefer the orientation with the smaller height for a new shelf --
    # conserves vertical room on the slab for whatever shelves follow.
    candidates = [
        (w, h, rotated) for w, h, rotated in orientations
        if w <= slab_length_mm and cursor_y + gap_above + h <= slab_width_mm
    ]
    if not candidates:
        return None
    w, h, rotated = min(candidates, key=lambda c: c[1])

    y = cursor_y + gap_above
    shelf = _Shelf(y_start=y, height=h, width=slab_length_mm)
    shelf.cursor_x = w
    shelf.remaining_width = slab_length_mm - w
    shelves.append(shelf)
    return Decimal("0"), y, w, h, rotated, True
