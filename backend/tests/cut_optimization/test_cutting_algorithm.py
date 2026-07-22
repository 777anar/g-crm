"""Pure unit tests for the shelf-packing nesting algorithm -- no DB, no
app_client, since this is domain logic with zero framework dependency."""
from decimal import Decimal

from modules.cut_optimization.domain.cutting_algorithm import PieceSpec, pack_pieces


def test_single_piece_fits_and_computes_utilization():
    result = pack_pieces(
        slab_length_mm=Decimal("3200"),
        slab_width_mm=Decimal("1600"),
        kerf_mm=Decimal("3"),
        pieces=[PieceSpec(label="Countertop", length_mm=Decimal("2000"), width_mm=Decimal("800"), quantity=1)],
    )
    assert result.all_placed
    assert len(result.placements) == 1
    p = result.placements[0]
    assert p.x_mm == Decimal("0")
    assert p.y_mm == Decimal("0")
    assert p.length_mm == Decimal("2000")
    assert p.width_mm == Decimal("800")
    assert result.placed_area_m2 == Decimal("1.6")
    assert result.total_area_m2 == Decimal("5.12")
    assert result.utilization_pct == (Decimal("1.6") / Decimal("5.12") * 100).quantize(Decimal("0.01"))


def test_pieces_in_same_shelf_are_separated_by_kerf():
    result = pack_pieces(
        slab_length_mm=Decimal("2000"),
        slab_width_mm=Decimal("1000"),
        kerf_mm=Decimal("5"),
        pieces=[
            PieceSpec(label="A", length_mm=Decimal("500"), width_mm=Decimal("400"), quantity=1, allow_rotation=False),
            PieceSpec(label="B", length_mm=Decimal("500"), width_mm=Decimal("400"), quantity=1, allow_rotation=False),
        ],
    )
    assert result.all_placed
    by_label = {p.label: p for p in result.placements}
    # Both pieces land in the same shelf (same y); the second starts at
    # least kerf_mm past the first piece's right edge.
    assert by_label["A"].y_mm == by_label["B"].y_mm
    first, second = sorted(result.placements, key=lambda p: p.x_mm)
    assert second.x_mm >= first.x_mm + first.length_mm + Decimal("5")


def test_rotation_used_when_it_lets_a_piece_fit():
    # A piece that only fits the slab's width if rotated 90 degrees.
    result = pack_pieces(
        slab_length_mm=Decimal("1000"),
        slab_width_mm=Decimal("1200"),
        kerf_mm=Decimal("0"),
        pieces=[PieceSpec(label="Tall", length_mm=Decimal("1200"), width_mm=Decimal("900"), quantity=1, allow_rotation=True)],
    )
    assert result.all_placed
    p = result.placements[0]
    assert p.rotated is True
    assert p.length_mm == Decimal("900")
    assert p.width_mm == Decimal("1200")


def test_rotation_disallowed_piece_that_only_fits_rotated_is_unplaced():
    result = pack_pieces(
        slab_length_mm=Decimal("1000"),
        slab_width_mm=Decimal("1200"),
        kerf_mm=Decimal("0"),
        pieces=[PieceSpec(label="Tall", length_mm=Decimal("1200"), width_mm=Decimal("900"), quantity=1, allow_rotation=False)],
    )
    assert not result.all_placed
    assert result.unplaced[0].label == "Tall"
    assert "every allowed orientation" in result.unplaced[0].reason


def test_piece_larger_than_slab_in_every_orientation_is_unplaced_with_reason():
    result = pack_pieces(
        slab_length_mm=Decimal("1000"),
        slab_width_mm=Decimal("1000"),
        kerf_mm=Decimal("0"),
        pieces=[PieceSpec(label="Huge", length_mm=Decimal("5000"), width_mm=Decimal("5000"), quantity=1)],
    )
    assert not result.all_placed
    assert result.unplaced[0].reason == "Piece exceeds the slab's dimensions in every allowed orientation"
    assert result.placements == []


def test_overflow_pieces_are_reported_unplaced_not_dropped_silently():
    # Slab only has room for one of these two identical large pieces.
    result = pack_pieces(
        slab_length_mm=Decimal("1000"),
        slab_width_mm=Decimal("1000"),
        kerf_mm=Decimal("0"),
        pieces=[PieceSpec(label="Slab-filler", length_mm=Decimal("900"), width_mm=Decimal("900"), quantity=2, allow_rotation=False)],
    )
    assert len(result.placements) == 1
    assert len(result.unplaced) == 1
    assert result.unplaced[0].instance_index == 2
    assert result.unplaced[0].reason == "No remaining space on the slab fits this piece"


def test_multiple_shelves_stack_with_kerf_between_rows():
    result = pack_pieces(
        slab_length_mm=Decimal("1000"),
        slab_width_mm=Decimal("1000"),
        kerf_mm=Decimal("10"),
        pieces=[
            PieceSpec(label="Row1", length_mm=Decimal("900"), width_mm=Decimal("300"), quantity=1, allow_rotation=False),
            PieceSpec(label="Row2", length_mm=Decimal("900"), width_mm=Decimal("300"), quantity=1, allow_rotation=False),
        ],
    )
    assert result.all_placed
    first, second = sorted(result.placements, key=lambda p: p.y_mm)
    assert second.y_mm >= first.y_mm + first.width_mm + Decimal("10")


def test_larger_pieces_are_placed_before_smaller_ones_regardless_of_input_order():
    result = pack_pieces(
        slab_length_mm=Decimal("2000"),
        slab_width_mm=Decimal("1000"),
        kerf_mm=Decimal("0"),
        pieces=[
            PieceSpec(label="Small", length_mm=Decimal("100"), width_mm=Decimal("100"), quantity=1, allow_rotation=False),
            PieceSpec(label="Big", length_mm=Decimal("1000"), width_mm=Decimal("1000"), quantity=1, allow_rotation=False),
        ],
    )
    assert result.all_placed
    big = next(p for p in result.placements if p.label == "Big")
    # The big piece claims the first shelf at the origin, having been
    # placed first despite appearing second in the input list.
    assert big.x_mm == Decimal("0")
    assert big.y_mm == Decimal("0")


def test_quantity_expands_into_individually_placed_instances():
    result = pack_pieces(
        slab_length_mm=Decimal("3000"),
        slab_width_mm=Decimal("1000"),
        kerf_mm=Decimal("2"),
        pieces=[PieceSpec(label="Tile", length_mm=Decimal("300"), width_mm=Decimal("300"), quantity=5, allow_rotation=False)],
    )
    assert result.all_placed
    assert len(result.placements) == 5
    assert {p.instance_index for p in result.placements} == {1, 2, 3, 4, 5}


def test_full_utilization_slab_reports_zero_waste():
    result = pack_pieces(
        slab_length_mm=Decimal("1000"),
        slab_width_mm=Decimal("1000"),
        kerf_mm=Decimal("0"),
        pieces=[PieceSpec(label="Exact", length_mm=Decimal("1000"), width_mm=Decimal("1000"), quantity=1, allow_rotation=False)],
    )
    assert result.utilization_pct == Decimal("100.00")
    assert result.waste_area_m2 == Decimal("0")
