"""Pure arithmetic helpers for recomputing quote totals."""
from decimal import ROUND_HALF_UP, Decimal
from typing import List

from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem
from modules.sales.infrastructure.models.quote_section_measurement import QuoteSectionMeasurement

_ZERO = Decimal("0")
_TWO = Decimal("0.01")


def _round2(v: Decimal) -> Decimal:
    return v.quantize(_TWO, rounding=ROUND_HALF_UP)


def _round4(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def compute_measurement(m: QuoteSectionMeasurement) -> None:
    """Recompute area_m2 and required_area_m2 on a measurement row in-place."""
    if m.length_mm is not None and m.width_mm is not None:
        area = _round4(
            Decimal(str(m.length_mm)) * Decimal(str(m.width_mm)) * m.quantity / Decimal("1000000")
        )
        m.area_m2 = area
        if not m.override_required_area:
            waste = Decimal(str(m.waste_pct)) / Decimal("100")
            m.required_area_m2 = _round4(area * (Decimal("1") + waste))
    else:
        m.area_m2 = None
        if not m.override_required_area:
            m.required_area_m2 = None


def recompute_section(section: QuoteSection, items: List[QuoteSectionItem], measurements: List[QuoteSectionMeasurement]) -> None:
    """Recompute section subtotals and total_measured_area in-place."""
    total_sale = _ZERO
    total_cost = _ZERO
    for item in items:
        item.line_total_sale = _round2(Decimal(str(item.quantity)) * Decimal(str(item.unit_sale_price)))
        item.line_total_cost = _round2(Decimal(str(item.quantity)) * Decimal(str(item.unit_cost_price)))
        total_sale += item.line_total_sale
        total_cost += item.line_total_cost
    section.subtotal_sale = _round2(total_sale)
    section.subtotal_cost = _round2(total_cost)

    measured = _ZERO
    has_measured = False
    for m in measurements:
        if m.required_area_m2 is not None:
            measured += Decimal(str(m.required_area_m2))
            has_measured = True
    section.total_measured_area = _round4(measured) if has_measured else None


def recompute_quote(quote: Quote, sections: List[QuoteSection]) -> None:
    """Recompute quote-level totals from section subtotals in-place."""
    gross = sum((Decimal(str(s.subtotal_sale)) for s in sections), _ZERO)
    quote.subtotal_gross = _round2(gross)

    if quote.discount_type == "percent":
        quote.discount_amount = _round2(gross * Decimal(str(quote.discount_value)) / Decimal("100"))
    elif quote.discount_type == "fixed":
        quote.discount_amount = _round2(Decimal(str(quote.discount_value)))
    else:
        quote.discount_amount = _ZERO

    quote.subtotal_after_discount = _round2(gross - quote.discount_amount)
    quote.vat_amount = _round2(quote.subtotal_after_discount * Decimal(str(quote.vat_rate)) / Decimal("100"))
    quote.total_final = _round2(quote.subtotal_after_discount + quote.vat_amount)

    total_cost = sum((Decimal(str(s.subtotal_cost)) for s in sections), _ZERO)
    quote.total_internal_cost = _round2(total_cost)
    quote.total_profit = _round2(quote.subtotal_after_discount - total_cost)

    if quote.subtotal_after_discount > _ZERO:
        quote.profit_margin_pct = _round2(quote.total_profit / quote.subtotal_after_discount * Decimal("100"))
    else:
        quote.profit_margin_pct = _ZERO
