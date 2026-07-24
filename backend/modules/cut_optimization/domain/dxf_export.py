"""CNC/machine-ready export (Phase 20): converts a persisted optimization
result's already-in-real-millimeters placement coordinates into a DXF file
a CNC/waterjet controller (or any CAM software) can import directly --
the same coordinate data the SVG visualization already renders, just
handed to a different output format. Pure domain logic: takes plain
dicts (as already stored on `CutOptimizationRun.placements` / `.pieces`),
no ORM/FastAPI dependency, so it's independently testable and reusable
for both a single-slab run and a multi-slab batch run.
"""
import io
from decimal import Decimal
from typing import Iterable, List

import ezdxf

SLAB_LAYER = "SLAB"
CUT_LAYER = "CUT"
LABEL_LAYER = "LABELS"

# Horizontal gap (mm) between adjacent slabs when several are laid out
# side by side in one batch-run DXF file -- purely a drawing convenience
# so slab boundaries never visually touch or overlap; has no effect on
# any placement's own coordinates.
BATCH_SLAB_GAP_MM = Decimal("200")


def _new_document():
    doc = ezdxf.new("R2010")
    doc.layers.add(SLAB_LAYER, color=7)
    doc.layers.add(CUT_LAYER, color=1)
    doc.layers.add(LABEL_LAYER, color=3)
    return doc


def _draw_slab_boundary(msp, *, x_offset: Decimal, length_mm: Decimal, width_mm: Decimal) -> None:
    x0, y0 = float(x_offset), 0.0
    x1, y1 = float(x_offset + length_mm), float(width_mm)
    msp.add_lwpolyline(
        [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
        close=True,
        dxfattribs={"layer": SLAB_LAYER},
    )


def _draw_placement(msp, *, x_offset: Decimal, placement: dict) -> None:
    x = float(Decimal(str(placement["x_mm"])) + x_offset)
    y = float(Decimal(str(placement["y_mm"])))
    w = float(Decimal(str(placement["length_mm"])))
    h = float(Decimal(str(placement["width_mm"])))
    msp.add_lwpolyline(
        [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
        close=True,
        dxfattribs={"layer": CUT_LAYER},
    )
    label = str(placement.get("label", ""))
    msp.add_text(
        label,
        height=min(w, h) * 0.15 or 10,
        dxfattribs={"layer": LABEL_LAYER},
    ).set_placement((x + w / 2, y + h / 2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)


def build_single_slab_dxf(*, slab_length_mm, slab_width_mm, placements: Iterable[dict]) -> bytes:
    doc = _new_document()
    msp = doc.modelspace()
    _draw_slab_boundary(msp, x_offset=Decimal("0"), length_mm=Decimal(str(slab_length_mm)), width_mm=Decimal(str(slab_width_mm)))
    for placement in placements:
        _draw_placement(msp, x_offset=Decimal("0"), placement=placement)
    return _serialize(doc)


def build_batch_dxf(*, slabs: List[dict], placements: Iterable[dict]) -> bytes:
    """One DXF file per batch run: every used slab laid out left-to-right
    with a fixed gap between them, each placement drawn on its own slab's
    boundary (matched by `slab_ref`, the same key the batch algorithm
    already tags every placement with)."""
    doc = _new_document()
    msp = doc.modelspace()

    x_offset_by_ref = {}
    cursor = Decimal("0")
    for slab in slabs:
        length_mm = Decimal(str(slab["length_mm"]))
        width_mm = Decimal(str(slab["width_mm"]))
        x_offset_by_ref[slab["slab_ref"]] = cursor
        _draw_slab_boundary(msp, x_offset=cursor, length_mm=length_mm, width_mm=width_mm)
        msp.add_text(
            slab["slab_ref"], height=float(width_mm) * 0.04 or 20, dxfattribs={"layer": LABEL_LAYER}
        ).set_placement((float(cursor), float(width_mm) + 30))
        cursor += length_mm + BATCH_SLAB_GAP_MM

    for placement in placements:
        x_offset = x_offset_by_ref.get(placement.get("slab_ref"), Decimal("0"))
        _draw_placement(msp, x_offset=x_offset, placement=placement)

    return _serialize(doc)


def _serialize(doc) -> bytes:
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")
