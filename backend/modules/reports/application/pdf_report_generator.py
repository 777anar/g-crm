"""PDF generation for Reports exports, using ReportLab -- same palette and
layout conventions as modules/sales/application/pdf_generator.py (the
established quote-PDF style) so exported reports look like they belong to
the same product.
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules.reports.application.export_adapter import ExportSections

_DARK = colors.HexColor("#1E293B")
_MID = colors.HexColor("#64748B")
_LIGHT = colors.HexColor("#F8FAFC")
_ACCENT = colors.HexColor("#3B82F6")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def generate_report_pdf(*, sections: ExportSections, company_name: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=sections.title,
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle("normal", parent=styles["Normal"], fontSize=9, leading=12, textColor=_DARK)
    small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=_MID)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, textColor=_DARK, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, textColor=_DARK, spaceBefore=10, spaceAfter=4)
    bold = ParagraphStyle("bold", parent=normal, fontName="Helvetica-Bold")

    story = []

    header_data = [[Paragraph(f"<b>{company_name}</b>", h1), Paragraph(sections.title, h1)]]
    header_tbl = Table(header_data, colWidths=[PAGE_W * 0.55 - MARGIN, PAGE_W * 0.45 - MARGIN])
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_tbl)
    story.append(Paragraph(f"Period: {sections.date_from} — {sections.date_to}", small))
    story.append(HRFlowable(width="100%", thickness=1, color=_ACCENT, spaceBefore=6, spaceAfter=6))

    # ── KPI grid ──────────────────────────────────────────────────────────────
    kpi_rows = []
    for i in range(0, len(sections.kpis), 2):
        pair = sections.kpis[i:i + 2]
        row = []
        for label, value in pair:
            row.append(Paragraph(f"{label}<br/><b>{value}</b>", normal))
        if len(row) == 1:
            row.append(Paragraph("", normal))
        kpi_rows.append(row)
    if kpi_rows:
        kpi_tbl = Table(kpi_rows, colWidths=[(PAGE_W - 2 * MARGIN) / 2] * 2)
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, _MID),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_tbl)

    # ── Tables ────────────────────────────────────────────────────────────────
    for table in sections.tables:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(table.title, h2))
        if not table.rows:
            story.append(Paragraph("No data for this period.", small))
            continue
        rows = [[Paragraph(f"<b>{h}</b>", small) for h in table.headers]]
        for r in table.rows:
            rows.append([Paragraph(str(c), normal) for c in r])
        col_w = (PAGE_W - 2 * MARGIN) / len(table.headers)
        tbl = Table(rows, colWidths=[col_w] * len(table.headers), repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _LIGHT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.3, _MID),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(tbl)

    doc.build(story)
    return buf.getvalue()
