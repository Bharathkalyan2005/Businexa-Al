"""PDF Report Builder using pure-Python ReportLab."""

from __future__ import annotations

import io
from typing import Any
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf_report(
    business_name: str,
    business_type: str,
    metrics: dict[str, Any],
    insights: list[str],
    narrative_sections: dict[str, str],
) -> bytes:
    """Build a PDF business report and return raw PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    primary_color = HexColor("#0f172a")
    accent_color = HexColor("#3b82f6")
    muted_color = HexColor("#64748b")

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=primary_color,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=muted_color,
    )

    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=accent_color,
        spaceBefore=14,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=HexColor("#334155"),
    )

    story = []

    # Header
    story.append(Paragraph("Businexa AI — Business Performance Report", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Business:</b> {business_name} | <b>Type:</b> {business_type.capitalize()}", subtitle_style))
    story.append(Spacer(1, 14))

    # KPI Table
    revenue_str = f"${metrics.get('revenue', 0):,.2f}" if metrics.get("revenue") is not None else "N/A"
    profit_str = f"${metrics.get('profit', 0):,.2f}" if metrics.get("profit") is not None else "N/A"
    orders_str = str(metrics.get("orders", 0))
    aov_str = f"${metrics.get('average_order_value', 0):.2f}" if metrics.get("average_order_value") is not None else "N/A"

    kpi_data = [
        ["Total Revenue", "Net Profit", "Total Orders", "Avg Order Value"],
        [revenue_str, profit_str, orders_str, aov_str],
    ]

    t = Table(kpi_data, colWidths=[130, 130, 130, 130])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#475569")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ])
    )
    story.append(t)
    story.append(Spacer(1, 16))

    # Executive Summary Section
    story.append(Paragraph("1. Executive Summary", h2_style))
    exec_text = narrative_sections.get(
        "executive_summary",
        f"This report provides a structured overview of {business_name}'s recent financial and operational metrics. Revenue reached {revenue_str} across {orders_str} logged transactions.",
    )
    story.append(Paragraph(exec_text, body_style))
    story.append(Spacer(1, 10))

    # Top Products Section
    top_products = metrics.get("top_products", [])
    if top_products:
        story.append(Paragraph("2. Top Product Performance", h2_style))
        prod_data = [["Rank", "Product Name", "Revenue", "% of Total"]]
        for idx, p in enumerate(top_products, 1):
            prod_data.append([str(idx), p.get("product", ""), f"${p.get('revenue', 0):,.2f}", f"{p.get('pct_of_total', 0)}%"])

        ptable = Table(prod_data, colWidths=[50, 250, 110, 110])
        ptable.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f8fafc")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(ptable)
        story.append(Spacer(1, 10))

    # AI Findings & Actionable Recommendations
    story.append(Paragraph("3. Key Insights & Recommended Actions", h2_style))
    if insights:
        for ins in insights:
            story.append(Paragraph(f"• {ins}", body_style))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("Maintain steady operations and continue tracking daily performance trends.", body_style))

    # Build document
    doc.build(story)
    return buffer.getvalue()
