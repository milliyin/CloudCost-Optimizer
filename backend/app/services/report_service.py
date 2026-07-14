from __future__ import annotations

import csv
from io import BytesIO, StringIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.dashboard_service import get_spend_summary
from app.services.findings_service import list_findings
from app.services.recommendation_service import list_recommendations


async def build_csv_report(db: AsyncSession, current_user: User) -> str:
    summary = await get_spend_summary(db, current_user)
    findings = await list_findings(db, current_user, finding_type=None, severity=None, status="all")
    recommendations = await list_recommendations(db, current_user, status="all")

    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["CloudCost Optimizer Report"])
    writer.writerow([])
    writer.writerow(["Spend summary"])
    writer.writerow(["Current month spend", summary.current_month_spend, summary.currency])
    writer.writerow(["Prior month spend", summary.prior_month_spend, summary.currency])
    writer.writerow(["Percent change", summary.percent_change if summary.percent_change is not None else "n/a"])
    writer.writerow(["Top service", summary.top_service or "n/a"])
    writer.writerow([])
    writer.writerow(["Findings"])
    writer.writerow(["ID", "Type", "Resource", "Severity", "Status", "Detected at"])
    for finding in findings:
        writer.writerow([finding.id, finding.finding_type, finding.resource_id, finding.severity, finding.status, finding.detected_at.isoformat()])
    writer.writerow([])
    writer.writerow(["Recommendations"])
    writer.writerow(["ID", "Action", "Resource", "Status", "Estimated monthly savings", "Decided at"])
    for recommendation in recommendations:
        writer.writerow(
            [
                recommendation.id,
                recommendation.action_type,
                recommendation.resource_id,
                recommendation.status,
                recommendation.estimated_monthly_savings if recommendation.estimated_monthly_savings is not None else "",
                recommendation.decided_at.isoformat() if recommendation.decided_at else "",
            ]
        )

    return buffer.getvalue()


async def build_pdf_report(db: AsyncSession, current_user: User) -> bytes:
    summary = await get_spend_summary(db, current_user)
    findings = await list_findings(db, current_user, finding_type=None, severity=None, status="all")
    recommendations = await list_recommendations(db, current_user, status="all")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.55 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#3525cd"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1b1b24"),
        spaceAfter=8,
        spaceBefore=10,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4b5563"),
    )
    label_style = ParagraphStyle(
        "ReportLabel",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6b7280"),
    )
    value_style = ParagraphStyle(
        "ReportValue",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#111827"),
    )
    hero_value_style = ParagraphStyle(
        "ReportHeroValue",
        parent=value_style,
        fontSize=20,
        leading=24,
        textColor=colors.white,
    )
    hero_label_style = ParagraphStyle(
        "ReportHeroLabel",
        parent=label_style,
        textColor=colors.HexColor("#ddd6fe"),
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=body_style,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#c4b5fd"),
    )
    hero_title_style = ParagraphStyle(
        "ReportHeroTitle",
        parent=title_style,
        textColor=colors.white,
    )
    hero_body_style = ParagraphStyle(
        "ReportHeroBody",
        parent=body_style,
        textColor=colors.HexColor("#ede9fe"),
    )
    cell_style = ParagraphStyle(
        "ReportCell",
        parent=body_style,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1f2937"),
    )

    story = []
    hero_table = Table(
        [
            [
                [
                    Paragraph("CloudCost Optimizer Report", hero_title_style),
                    Paragraph(f"Organization: <b>{current_user.organization.name}</b>", hero_body_style),
                    Paragraph(
                        "Executive-ready export of synced spend, findings, and recommendation history. "
                        "The app records review decisions only and does not apply AWS changes.",
                        hero_body_style,
                    ),
                ],
                [
                    Paragraph("Current month", hero_label_style),
                    Paragraph(f"{summary.current_month_spend:.2f} {summary.currency}", hero_value_style),
                    Paragraph("Generated from organization-scoped PostgreSQL sync data", meta_style),
                ],
            ]
        ],
        colWidths=[4.75 * inch, 2.05 * inch],
    )
    hero_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3525cd")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#3120bf")),
                ("LEFTPADDING", (0, 0), (-1, -1), 18),
                ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                ("TOPPADDING", (0, 0), (-1, -1), 18),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    story.extend([hero_table, Spacer(1, 14)])

    summary_table = Table(
        [
            [
                Paragraph("Current month spend", label_style),
                Paragraph("Prior month spend", label_style),
                Paragraph("Top service", label_style),
                Paragraph("Findings tracked", label_style),
            ],
            [
                Paragraph(f"{summary.current_month_spend:.2f} {summary.currency}", value_style),
                Paragraph(f"{summary.prior_month_spend:.2f} {summary.currency}", value_style),
                Paragraph(summary.top_service or "n/a", value_style),
                Paragraph(str(len(findings)), value_style),
            ],
        ],
        colWidths=[1.65 * inch, 1.6 * inch, 2.25 * inch, 1.0 * inch],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f0ff")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#d8d5f2")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e5f8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 14), Paragraph("Findings", section_style)])

    findings_rows = [[
        Paragraph("Severity", label_style),
        Paragraph("Type", label_style),
        Paragraph("Resource", label_style),
        Paragraph("Status", label_style),
        Paragraph("Detected", label_style),
    ]]
    for finding in findings[:25]:
        findings_rows.append(
            [
                Paragraph(finding.severity.upper(), cell_style),
                Paragraph(finding.finding_type.replace("_", " "), cell_style),
                Paragraph(finding.resource_id, cell_style),
                Paragraph(finding.status, cell_style),
                Paragraph(finding.detected_at.strftime("%Y-%m-%d %H:%M"), cell_style),
            ]
        )
    if len(findings_rows) == 1:
        findings_rows.append(
            [
                Paragraph("n/a", cell_style),
                Paragraph("No findings synced yet", cell_style),
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
            ]
        )
    findings_table = Table(findings_rows, colWidths=[0.9 * inch, 1.6 * inch, 2.2 * inch, 0.8 * inch, 1.35 * inch])
    findings_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#3525cd")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafaff")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([findings_table, Spacer(1, 14), Paragraph("Recommendations", section_style)])

    recommendation_rows = [[
        Paragraph("Status", label_style),
        Paragraph("Action", label_style),
        Paragraph("Resource", label_style),
        Paragraph("Savings / month", label_style),
        Paragraph("Decision note", label_style),
    ]]
    for recommendation in recommendations[:25]:
        recommendation_rows.append(
            [
                Paragraph(recommendation.status, cell_style),
                Paragraph(recommendation.action_type.replace("_", " "), cell_style),
                Paragraph(recommendation.resource_id, cell_style),
                Paragraph(
                    f"${recommendation.estimated_monthly_savings:.2f}" if recommendation.estimated_monthly_savings is not None else "Review only",
                    cell_style,
                ),
                Paragraph(recommendation.decision_reason or "-", cell_style),
            ]
        )
    if len(recommendation_rows) == 1:
        recommendation_rows.append(
            [
                Paragraph("n/a", cell_style),
                Paragraph("No recommendations yet", cell_style),
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
            ]
        )
    recommendations_table = Table(
        recommendation_rows,
        colWidths=[0.85 * inch, 1.7 * inch, 1.8 * inch, 1.1 * inch, 1.2 * inch],
    )
    recommendations_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eefbf1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#166534")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbfdfb")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend(
        [
            recommendations_table,
            Spacer(1, 12),
            Paragraph(
                "Approval in this report means the recommendation was accepted in the app workflow only. "
                "AWS resources must still be changed manually by a human outside this system.",
                body_style,
            ),
        ]
    )

    document.build(story)
    return buffer.getvalue()
