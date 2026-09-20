import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

from app.schemas.report import MonthlyReportResponse


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page numbers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_footer(num_pages)
            super().showPage()
        super().save()

    def draw_page_footer(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        # Footer line
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 28, 559, 28)
        # Footer text
        self.drawString(36, 18, "FinPilot — Personal Finance Analytics & Decision Support (Informational Only)")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(559, 18, page_str)
        self.restoreState()


def build_monthly_pdf(report: MonthlyReportResponse) -> bytes:
    """Renders a comprehensive, styled monthly financial report into PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E1B4B"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#4F46E5"),
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B"),
        alignment=2,  # Right align
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=12,
        spaceAfter=6,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#991B1B"),
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
    )
    table_cell_right = ParagraphStyle(
        "TableCellRight",
        parent=table_cell,
        alignment=2,
    )
    table_cell_bold_right = ParagraphStyle(
        "TableCellBoldRight",
        parent=table_cell_bold,
        alignment=2,
    )
    checklist_title = ParagraphStyle(
        "ChecklistTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
    )
    checklist_desc = ParagraphStyle(
        "ChecklistDesc",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("FinPilot", title_style),
            Paragraph(
                f"Statement Period: <b>{report.month_name}</b><br/>Generated: {datetime.now().strftime('%d %b %Y %H:%M')}",
                meta_style,
            ),
        ],
        [
            Paragraph("Monthly Financial Statement Report", subtitle_style),
            Paragraph(f"Currency: {report.currency}", meta_style),
        ],
    ]
    header_table = Table(header_data, colWidths=[340, 183])
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 2. Disclaimer Box
    disclaimer_box = Table(
        [[Paragraph(f"<b>IMPORTANT NOTICE:</b> {report.disclaimer}", disclaimer_style)]],
        colWidths=[523],
    )
    disclaimer_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#F87171")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(disclaimer_box)
    story.append(Spacer(1, 10))

    # 3. Cash Flow Summary Cards
    cf = report.cash_flow
    mom_str = f" ({'+' if (cf.mom_change_pct or 0) > 0 else ''}{cf.mom_change_pct}% MoM)" if cf.mom_change_pct is not None else ""
    
    kpi_data = [
        [
            Paragraph("<font size=7.5 color='#64748B'>TOTAL INCOME</font>", styles["Normal"]),
            Paragraph("<font size=7.5 color='#64748B'>TOTAL EXPENSES</font>", styles["Normal"]),
            Paragraph("<font size=7.5 color='#64748B'>NET SAVINGS</font>", styles["Normal"]),
            Paragraph("<font size=7.5 color='#64748B'>SAVINGS RATE</font>", styles["Normal"]),
        ],
        [
            Paragraph(f"<font size=12 color='#059669'><b>{cf.income_display}</b></font>", styles["Normal"]),
            Paragraph(f"<font size=12 color='#DC2626'><b>{cf.expense_display}</b></font>", styles["Normal"]),
            Paragraph(f"<font size=12 color='#2563EB'><b>{cf.net_savings_display}</b></font>", styles["Normal"]),
            Paragraph(f"<font size=12 color='#4F46E5'><b>{cf.savings_rate_pct}%</b></font>{mom_str}", styles["Normal"]),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 131, 131, 131])
    kpi_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )
    story.append(kpi_table)
    story.append(Spacer(1, 10))

    # 4. Executive Narrative
    story.append(Paragraph("<b>Executive Overview</b>", section_heading))
    narrative_box = Table(
        [[Paragraph(report.narrative, body_style)]],
        colWidths=[523],
    )
    narrative_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(narrative_box)
    story.append(Spacer(1, 10))

    # 5. Spending Breakdown Table
    story.append(Paragraph("<b>Top Spending Categories</b>", section_heading))
    cat_rows = [
        [
            Paragraph("<b>Category</b>", table_cell_bold),
            Paragraph("<b>Txn Count</b>", table_cell_bold_right),
            Paragraph("<b>Share (%)</b>", table_cell_bold_right),
            Paragraph("<b>Amount</b>", table_cell_bold_right),
        ]
    ]
    for c in report.top_categories:
        cat_rows.append([
            Paragraph(c.category, table_cell),
            Paragraph(str(c.transaction_count), table_cell_right),
            Paragraph(f"{c.pct_of_total}%", table_cell_right),
            Paragraph(c.amount_display, table_cell_bold_right),
        ])

    cat_table = Table(cat_rows, colWidths=[223, 80, 100, 120])
    cat_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(cat_table)
    story.append(Spacer(1, 10))

    # 6. Category Budgets & Adherence Table (if any)
    if report.budgets:
        story.append(Paragraph("<b>Budget Performance</b>", section_heading))
        b_rows = [
            [
                Paragraph("<b>Category</b>", table_cell_bold),
                Paragraph("<b>Monthly Limit</b>", table_cell_bold_right),
                Paragraph("<b>Spent</b>", table_cell_bold_right),
                Paragraph("<b>Remaining / Buffer</b>", table_cell_bold_right),
                Paragraph("<b>Status</b>", table_cell_bold_right),
            ]
        ]
        for b in report.budgets:
            status_color = "#059669" if b.status == "on_track" else ("#D97706" if b.status == "warning" else "#DC2626")
            status_label = b.status.replace("_", " ").upper()
            b_rows.append([
                Paragraph(b.category, table_cell),
                Paragraph(b.monthly_limit_display, table_cell_right),
                Paragraph(b.spent_display, table_cell_right),
                Paragraph(b.remaining_display, table_cell_right),
                Paragraph(f"<font color='{status_color}'><b>{status_label}</b> ({b.spent_pct}%)</font>", table_cell_right),
            ])

        b_table = Table(b_rows, colWidths=[143, 95, 95, 95, 95])
        b_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(b_table)
        story.append(Spacer(1, 10))

    # 7. Subscriptions & Commitments (if any)
    if report.recurring:
        story.append(Paragraph("<b>Recurring Commitments & Subscriptions</b>", section_heading))
        r_rows = [
            [
                Paragraph("<b>Merchant</b>", table_cell_bold),
                Paragraph("<b>Frequency</b>", table_cell_bold),
                Paragraph("<b>Status</b>", table_cell_bold),
                Paragraph("<b>Avg Amount</b>", table_cell_bold_right),
            ]
        ]
        for r in report.recurring:
            stat_color = "#059669" if r.status == "active" else "#D97706"
            r_rows.append([
                Paragraph(r.merchant, table_cell),
                Paragraph(r.frequency.capitalize(), table_cell),
                Paragraph(f"<font color='{stat_color}'><b>{r.status.replace('_', ' ').capitalize()}</b></font>", table_cell),
                Paragraph(r.avg_amount_display, table_cell_bold_right),
            ])

        r_table = Table(r_rows, colWidths=[203, 100, 110, 110])
        r_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(r_table)
        story.append(Spacer(1, 10))

    # 8. Detected Anomalies / Flags (if any)
    if report.anomalies:
        story.append(Paragraph("<b>Detected Statement Anomalies & Flags</b>", section_heading))
        anom_elements = []
        for a in report.anomalies:
            sev_color = "#DC2626" if a.severity in ["critical", "warning"] else "#2563EB"
            box_text = f"<font color='{sev_color}'><b>[{a.type.upper().replace('_', ' ')}]</b></font> {a.text}"
            anom_elements.append([Paragraph(box_text, table_cell)])

        anom_table = Table(anom_elements, colWidths=[523])
        anom_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#FEF3C7")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(anom_table)
        story.append(Spacer(1, 10))

    # 9. Actionable Optimization Checklist
    if report.action_items:
        story.append(Paragraph("<b>Actionable Decision Checklist</b>", section_heading))
        chk_elements = []
        for act in report.action_items:
            impact_badge = f"<font color='#DC2626'>[HIGH PRIORITY]</font>" if act.impact_type == "high" else (
                f"<font color='#D97706'>[MEDIUM PRIORITY]</font>" if act.impact_type == "medium" else "<font color='#2563EB'>[SAVINGS TIP]</font>"
            )
            pot_str = f" — <i>Potential Recovery/Savings: {act.potential_savings_display}</i>" if act.potential_savings_display else ""
            title_p = Paragraph(f"[  ] <b>{act.title}</b> {impact_badge}{pot_str}", checklist_title)
            desc_p = Paragraph(act.description, checklist_desc)
            chk_elements.append([title_p])
            chk_elements.append([desc_p])

        chk_table = Table(chk_elements, colWidths=[523])
        chk_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(KeepTogether([chk_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
