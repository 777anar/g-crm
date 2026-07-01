"""PDF generation for quotes using ReportLab.

Renders the section hierarchy: each named section becomes a headed block with
an item table and a section subtotal. The Delivery & Logistics section (if it
has items) is last. The global totals block follows.

Internal fields (cost, profit, internal_notes) are never included.
"""
import io
from decimal import Decimal
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from modules.sales.infrastructure.models.company_service_price import CompanyServicePrice
from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

# ── Colour palette (matches the G-STONE ERP brand from UI_UX_GUIDELINES) ─────
_DARK = colors.HexColor("#1E293B")
_MID = colors.HexColor("#64748B")
_LIGHT = colors.HexColor("#F8FAFC")
_ACCENT = colors.HexColor("#3B82F6")
_WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def _fmt(value, decimals: int = 2) -> str:
    """Format a Decimal or numeric as a localised-ish number string."""
    try:
        v = Decimal(str(value))
        return f"{v:,.{decimals}f}"
    except Exception:
        return str(value)


def _currency(value, currency: str = "AZN") -> str:
    return f"{_fmt(value)} {currency}"


def generate_quote_pdf(
    *,
    quote: Quote,
    project_name: str,
    project_type: str,
    project_address: Optional[str],
    customer_name: str,
    customer_phone: Optional[str],
    customer_email: Optional[str],
    company_name: str,
    company_address: Optional[str],
    company_phone: Optional[str],
    company_email: Optional[str],
    prepared_by_name: Optional[str],
    sections: List[QuoteSection],
    items_by_section: dict,  # section.id → List[QuoteSectionItem]
    is_draft: bool = False,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"Quote {quote.quote_number}",
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle("normal", parent=styles["Normal"], fontSize=9, leading=12, textColor=_DARK)
    small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=_MID)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, textColor=_DARK, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, textColor=_DARK, spaceBefore=8, spaceAfter=4)
    section_hdr = ParagraphStyle("sechdr", parent=styles["Normal"], fontSize=10, textColor=_WHITE,
                                  fontName="Helvetica-Bold")
    bold = ParagraphStyle("bold", parent=normal, fontName="Helvetica-Bold")
    total_label = ParagraphStyle("totlbl", parent=normal, fontName="Helvetica-Bold", fontSize=10)
    grand_total = ParagraphStyle("grand", parent=normal, fontName="Helvetica-Bold", fontSize=12, textColor=_ACCENT)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b>", h1),
            Paragraph(
                f"{company_address or ''}<br/>{company_phone or ''}<br/>{company_email or ''}",
                small,
            ),
        ]
    ]
    header_tbl = Table(header_data, colWidths=[PAGE_W * 0.55 - MARGIN, PAGE_W * 0.45 - MARGIN])
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0, colors.white)]))
    story.append(header_tbl)
    story.append(HRFlowable(width="100%", thickness=1, color=_ACCENT, spaceAfter=6))

    # ── Quote identity ────────────────────────────────────────────────────────
    title_text = "QUOTATION" + (" — DRAFT" if is_draft else "")
    meta_data = [
        [Paragraph(title_text, h1),
         Paragraph(
             f"<b>Quote No:</b> {quote.quote_number}<br/>"
             f"<b>Date:</b> {str(quote.created_at)[:10]}<br/>"
             + (f"<b>Valid until:</b> {quote.valid_until}" if quote.valid_until else ""),
             small,
         )],
    ]
    meta_tbl = Table(meta_data, colWidths=[PAGE_W * 0.55 - MARGIN, PAGE_W * 0.45 - MARGIN])
    meta_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0, colors.white)]))
    story.append(meta_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Customer / Project block ──────────────────────────────────────────────
    cp_data = [
        [
            Paragraph(
                f"<b>PREPARED FOR</b><br/>{customer_name}<br/>"
                f"{customer_phone or ''}<br/>{customer_email or ''}",
                normal,
            ),
            Paragraph(
                f"<b>PROJECT</b><br/>{project_name}<br/>"
                f"{project_type.replace('_',' ').title()}<br/>{project_address or ''}",
                normal,
            ),
        ]
    ]
    cp_tbl = Table(cp_data, colWidths=[(PAGE_W - 2 * MARGIN) / 2, (PAGE_W - 2 * MARGIN) / 2])
    cp_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, _MID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cp_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── Sections ──────────────────────────────────────────────────────────────
    col_w = PAGE_W - 2 * MARGIN
    desc_w = col_w * 0.50
    qty_w = col_w * 0.10
    unit_w = col_w * 0.10
    price_w = col_w * 0.15
    total_w = col_w * 0.15

    def _item_table(section_items: List[QuoteSectionItem], currency: str) -> Table:
        rows = [
            [
                Paragraph("<b>Description</b>", small),
                Paragraph("<b>Qty</b>", small),
                Paragraph("<b>Unit</b>", small),
                Paragraph("<b>Unit price</b>", small),
                Paragraph("<b>Total</b>", small),
            ]
        ]
        for it in section_items:
            rows.append([
                Paragraph(it.description, normal),
                Paragraph(_fmt(it.quantity, 3).rstrip("0").rstrip("."), normal),
                Paragraph(it.unit, normal),
                Paragraph(_fmt(it.unit_sale_price), normal),
                Paragraph(_fmt(it.line_total_sale), normal),
            ])
        tbl = Table(rows, colWidths=[desc_w, qty_w, unit_w, price_w, total_w], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _LIGHT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.3, _MID),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return tbl

    for sec in sections:
        section_items = items_by_section.get(str(sec.id), [])
        if not section_items:
            continue

        # Section header row.
        hdr_tbl = Table(
            [[Paragraph(sec.name.upper(), section_hdr)]],
            colWidths=[col_w],
        )
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _DARK),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(hdr_tbl)
        story.append(_item_table(section_items, quote.currency))

        # Section subtotal right-aligned.
        sub_row = Table(
            [[Paragraph(""), Paragraph(f"Section subtotal: {_currency(sec.subtotal_sale, quote.currency)}", bold)]],
            colWidths=[col_w * 0.6, col_w * 0.4],
        )
        sub_row.setStyle(TableStyle([
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("RIGHTPADDING", (1, 0), (1, 0), 4),
        ]))
        story.append(sub_row)
        story.append(Spacer(1, 4 * mm))

    # ── Totals block ──────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=_MID, spaceAfter=4))

    def _total_row(label: str, value: str, bold_style=False) -> List:
        lbl_style = bold if bold_style else normal
        val_style = grand_total if bold_style else normal
        return [
            Paragraph(""),
            Paragraph(f"{label}:", lbl_style),
            Paragraph(value, val_style),
        ]

    totals_rows = [_total_row("Subtotal", _currency(quote.subtotal_gross, quote.currency))]
    if quote.discount_type != "none" and quote.discount_amount > Decimal("0"):
        disc_label = f"Discount ({_fmt(quote.discount_value)}{'%' if quote.discount_type == 'percent' else ' ' + quote.currency})"
        totals_rows.append(_total_row(disc_label, f"− {_currency(quote.discount_amount, quote.currency)}"))
        totals_rows.append(_total_row("After discount", _currency(quote.subtotal_after_discount, quote.currency)))
    if quote.vat_rate > Decimal("0"):
        totals_rows.append(_total_row(f"VAT ({_fmt(quote.vat_rate, 0)}%)", _currency(quote.vat_amount, quote.currency)))
    totals_rows.append(_total_row("TOTAL", _currency(quote.total_final, quote.currency), bold_style=True))

    totals_tbl = Table(totals_rows, colWidths=[col_w * 0.45, col_w * 0.30, col_w * 0.25])
    totals_tbl.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (-1, -1), (-1, -1), 0.5, _DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(totals_tbl)

    # ── Customer notes ────────────────────────────────────────────────────────
    if quote.customer_notes:
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", thickness=0.3, color=_MID))
        story.append(Paragraph("<b>Notes</b>", bold))
        story.append(Paragraph(quote.customer_notes, normal))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=_MID))
    footer_text = f"Prepared by: {prepared_by_name or 'N/A'}    |    {company_name}"
    story.append(Paragraph(footer_text, small))

    doc.build(story)
    return buf.getvalue()
