import io
import os
import re
import logging
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# Try registering Unicode/Hebrew font
HEBREW_FONT_NAME = "Helvetica"
for candidate in [
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
]:
    if os.path.exists(candidate):
        try:
            pdfmetrics.registerFont(TTFont("ArialHebrew", candidate))
            HEBREW_FONT_NAME = "ArialHebrew"
            break
        except Exception:
            pass

def _bidi_format(text: str) -> str:
    """Format Hebrew text for RTL PDF rendering using python-bidi if Hebrew characters are present."""
    if not text:
        return ""
    # Check if string contains Hebrew characters
    if re.search(r'[\u0590-\u05FF]', text):
        try:
            from bidi.algorithm import get_display
            return get_display(str(text))
        except Exception:
            return str(text)
    return str(text)

class ExportService:
    """Service for exporting detection logs and analytics to PDF and Excel formats."""

    def export_excel(self, records: List[Dict[str, Any]]) -> bytes:
        """Generate a professionally styled Excel workbook from detection records.
        
        Args:
            records: List of detection dictionaries.
            
        Returns:
            Raw bytes of the generated .xlsx file.
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "Vision Detections"

        headers = [
            "Timestamp (UTC)",
            "Object Name",
            "Category",
            "Confidence",
            "Detected Entities",
            "Detected Text (OCR)",
            "Price (₪)",
            "Trigger",
            "Visual Description"
        ]
        ws.append(headers)

        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align

        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )

        stripe_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        for row_idx, r in enumerate(records, start=2):
            ts = r.get("timestamp", "")
            if isinstance(ts, str) and len(ts) > 19:
                ts = ts[:19].replace("T", " ")

            entities = ", ".join(r.get("detected_entities", []))
            prod_info = r.get("product_info") or {}
            price = prod_info.get("estimated_price_ils", "") if isinstance(prod_info, dict) else ""

            row_data = [
                str(ts),
                r.get("object_name", ""),
                r.get("category", ""),
                f"{r.get('confidence', 0.0) * 100:.1f}%",
                entities,
                r.get("detected_text") or "",
                price,
                r.get("trigger_source", "manual"),
                (r.get("visual_description", "") or "")[:150]
            ]
            ws.append(row_data)

            is_even = (row_idx % 2 == 0)
            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=row_idx, column=col_num)
                cell.border = thin_border
                cell.alignment = left_align
                if is_even:
                    cell.fill = stripe_fill

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def export_pdf(self, records: List[Dict[str, Any]]) -> bytes:
        """Generate a landscape PDF report from detection records.
        
        Args:
            records: List of detection dictionaries.
            
        Returns:
            Raw bytes of the generated .pdf file.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Heading1"],
            fontName=HEBREW_FONT_NAME,
            fontSize=18,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=10
        )
        subtitle_style = ParagraphStyle(
            name="SubTitleStyle",
            parent=styles["Normal"],
            fontName=HEBREW_FONT_NAME,
            fontSize=10,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=15
        )
        cell_style = ParagraphStyle(
            name="CellText",
            parent=styles["Normal"],
            fontName=HEBREW_FONT_NAME,
            fontSize=8,
            textColor=colors.HexColor("#1E293B")
        )

        elements = [
            Paragraph("Smart Camera Vision Recognition - Audit Report", title_style),
            Paragraph(f"Exported {len(records)} recent records from MongoDB Atlas | Model: Gemini 3.5 Flash Lite", subtitle_style),
            Spacer(1, 10)
        ]

        table_data = [
            ["Timestamp", "Object", "Category", "Confidence", "Entities", "Trigger", "Description / Insight"]
        ]

        for r in records[:30]:  # Limit to 30 items for clean PDF pagination
            ts = r.get("timestamp", "")
            if isinstance(ts, str) and len(ts) > 16:
                ts = ts[:16].replace("T", " ")

            entities = ", ".join(r.get("detected_entities", []))[:30]
            desc = r.get("enrichment_summary") or r.get("visual_description") or ""
            desc = desc[:70]

            table_data.append([
                Paragraph(str(ts), cell_style),
                Paragraph(_bidi_format(str(r.get("object_name", ""))), cell_style),
                Paragraph(_bidi_format(str(r.get("category", ""))), cell_style),
                Paragraph(f"{r.get('confidence', 0.0) * 100:.0f}%", cell_style),
                Paragraph(_bidi_format(entities), cell_style),
                Paragraph(str(r.get("trigger_source", "manual")), cell_style),
                Paragraph(_bidi_format(desc), cell_style)
            ])

        col_widths = [80, 100, 90, 60, 120, 80, 220]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

# Singleton service instance
export_service = ExportService()
