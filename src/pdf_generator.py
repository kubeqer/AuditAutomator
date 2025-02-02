from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from sqlalchemy.orm import Session
from database import get_report, GeneratedReport, OpenSCAP, Lynis
from loguru import logger
import re


def sanitize_text(text: str) -> str:
    """Replaces <br> tags (and similar variants) with newline characters."""
    if text:
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    return text


def generate_audit_report_pdf(session: Session, report_id: int, pdf_path) -> None:
    """
    Generates an Audit Report PDF for the given report_id.

    The PDF includes:
      - A main page with the report title and date.
      - A well-formatted report metadata section.
      - A section for each GeneratedReport record.
        - OpenSCAP records display their title and description.
        - Lynis (Detail/Suggestion) records use service name and field as headers.
        - Only unique Lynis records (based on lynis_json_id) are printed.

    Args:
        session (Session): The active SQLAlchemy session.
        report_id (int): The ID of the report.
        pdf_path: The file path where the PDF will be saved.
    """

    report_data = get_report(session, report_id)
    if not report_data:
        logger.error(f"Report with ID {report_id} not found.")
        return

    gen_records = (
        session.query(GeneratedReport)
        .filter(GeneratedReport.report_id == report_id)
        .all()
    )
    pdf_filename = str(pdf_path)
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
    styles = getSampleStyleSheet()

    # Define styles
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=18,
        alignment=1,
        textColor=colors.darkblue,
        spaceAfter=16,
    )

    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Heading2"],
        fontSize=14,
        alignment=1,
        textColor=colors.black,
        spaceAfter=12,
    )

    normal_style = styles["Normal"]

    elements = []

    # === Main Page ===
    elements.append(Paragraph("Audit Report", title_style))
    elements.append(Spacer(1, 10))

    # Report Metadata Table
    metadata_table = Table(
        [
            ["Report Date:", report_data.get("date")],
            ["Total Findings:", len(gen_records)],
        ],
        colWidths=[120, 300],
    )

    metadata_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(metadata_table)
    elements.append(Spacer(1, 20))

    # Separator Line
    elements.append(Paragraph("<hr width='100%' color='black'/>", normal_style))
    elements.append(Spacer(1, 10))
    elements.append(PageBreak())

    # === Report Content ===
    printed_lynis_ids = set()

    for record in gen_records:
        title = ""
        description = ""

        if record.object_a_type.lower() == "openscap":
            db_obj = (
                session.query(OpenSCAP)
                .filter(OpenSCAP.id == record.object_a_id)
                .first()
            )
            if db_obj:
                title = db_obj.title
                description = db_obj.description or ""

        elif record.object_a_type.lower() in ["detail", "suggestion"]:
            db_obj = session.query(Lynis).filter(Lynis.id == record.object_a_id).first()
            if db_obj:
                lynis_id = db_obj.lynis_json_id
                if lynis_id and lynis_id in printed_lynis_ids:
                    continue
                if lynis_id:
                    printed_lynis_ids.add(lynis_id)

                title = db_obj.service if db_obj.service else "Lynis Record"
                if db_obj.field:
                    title += f" ({db_obj.field})"

                if record.object_a_type.lower() == "suggestion" and lynis_id:
                    title = f"Suggestion {lynis_id}: {title}"

                description = (
                    db_obj.long_description
                    if db_obj.long_description
                    else (db_obj.desc or "")
                )

        else:
            title = f"Unknown Type ({record.object_a_type})"
            description = ""

        # Sanitize the text
        title = sanitize_text(title)
        description = sanitize_text(description)

        # Add section to PDF
        elements.append(Paragraph(title, subtitle_style))
        elements.append(Paragraph(description, normal_style))
        elements.append(Spacer(1, 12))

    doc.build(elements)
    logger.info(f"Audit Report PDF generated: {pdf_filename}")
