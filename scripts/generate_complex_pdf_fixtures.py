from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT_DIR = Path("examples/real_pdfs")


class FlowChart(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = 165 * mm
        self.height = 92 * mm

    def draw(self) -> None:
        canvas = self.canv
        boxes = [
            (8 * mm, 62 * mm, 38 * mm, 18 * mm, "Receive\nDocuments"),
            (60 * mm, 62 * mm, 38 * mm, 18 * mm, "MinerU\nParse"),
            (112 * mm, 62 * mm, 38 * mm, 18 * mm, "Quality\nGate"),
            (8 * mm, 22 * mm, 38 * mm, 18 * mm, "Retry\nOCR/API"),
            (60 * mm, 22 * mm, 38 * mm, 18 * mm, "Build\nChunks"),
            (112 * mm, 22 * mm, 38 * mm, 18 * mm, "Trace\nArchive"),
        ]
        canvas.setStrokeColor(colors.HexColor("#305C89"))
        canvas.setFillColor(colors.HexColor("#EAF2F8"))
        for x, y, w, h, label in boxes:
            canvas.roundRect(x, y, w, h, 3 * mm, fill=1, stroke=1)
            canvas.setFillColor(colors.HexColor("#17324D"))
            text = canvas.beginText(x + 4 * mm, y + 11 * mm)
            text.setFont("Helvetica-Bold", 8)
            for line in label.splitlines():
                text.textLine(line)
            canvas.drawText(text)
            canvas.setFillColor(colors.HexColor("#EAF2F8"))
        canvas.setStrokeColor(colors.HexColor("#6C7A89"))
        arrows = [
            (46 * mm, 71 * mm, 60 * mm, 71 * mm),
            (98 * mm, 71 * mm, 112 * mm, 71 * mm),
            (131 * mm, 62 * mm, 131 * mm, 40 * mm),
            (112 * mm, 31 * mm, 98 * mm, 31 * mm),
            (60 * mm, 31 * mm, 46 * mm, 31 * mm),
            (27 * mm, 40 * mm, 27 * mm, 62 * mm),
        ]
        for x1, y1, x2, y2 in arrows:
            canvas.line(x1, y1, x2, y2)
            canvas.circle(x2, y2, 1.1 * mm, fill=1, stroke=0)


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    base["Title"].fontName = "Helvetica-Bold"
    base["Heading1"].fontName = "Helvetica-Bold"
    base["Heading2"].fontName = "Helvetica-Bold"
    base["BodyText"].fontName = "Helvetica"
    base.add(
        ParagraphStyle(
            name="Small",
            parent=base["BodyText"],
            fontSize=8,
            leading=10,
        )
    )
    return base


def build_pdf(path: Path, title: str, story: list[object]) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
    )
    doc.build(story)


def table(data: list[list[str]], header: bool = True) -> Table:
    result = Table(data, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9AA6B2")),
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7),
            ]
        )
    result.setStyle(TableStyle(style))
    return result


def financial_report() -> None:
    s = styles()
    rows = [["Line Item", "2024 Q1", "2024 Q2", "2024 Q3", "2024 Q4", "FY 2024"]]
    values = [
        ("Product revenue", 12340, 13110, 14220, 15680),
        ("Service revenue", 5220, 5480, 6040, 6330),
        ("Channel rebate", -740, -810, -860, -910),
        ("Cloud cost", -3180, -3440, -3720, -3990),
        ("Sales expense", -2280, -2440, -2510, -2690),
        ("R&D expense", -3100, -3260, -3490, -3710),
        ("General expense", -1420, -1500, -1605, -1710),
        ("Tax adjustment", -260, -280, -310, -330),
    ]
    for name, q1, q2, q3, q4 in values:
        rows.append([name, f"{q1:,}", f"{q2:,}", f"{q3:,}", f"{q4:,}", f"{q1 + q2 + q3 + q4:,}"])
    totals = [sum(item[i] for item in values) for i in range(1, 5)]
    rows.append(["Total operating result", *(f"{v:,}" for v in totals), f"{sum(totals):,}"])

    story: list[object] = [
        Paragraph("Complex Financial Report Fixture", s["Title"]),
        Paragraph("Document ID: FIN-2026-CASE-01", s["BodyText"]),
        Paragraph("Reporting Period: 2024-01-01 to 2024-12-31", s["BodyText"]),
        Paragraph("Purpose: test dense numeric extraction, total-row validation, and provenance logging.", s["BodyText"]),
        Spacer(1, 8),
        Paragraph("1. Executive Summary", s["Heading1"]),
        Paragraph(
            "The report contains quarterly financial data, negative adjustments, cross-page notes, and a final total row. "
            "The agent should preserve table structure, numeric facts, dates, and warning signals.",
            s["BodyText"],
        ),
        PageBreak(),
        Paragraph("2. Operating Result Table", s["Heading1"]),
        table(rows),
        Spacer(1, 8),
        Paragraph("Review note: totals must be checked against comparable numeric rows.", s["Small"]),
        PageBreak(),
        Paragraph("3. Audit Notes", s["Heading1"]),
        Paragraph("Risk: channel rebate values require manual confirmation against the source ledger.", s["BodyText"]),
        Paragraph("Recommendation: re-run OCR if any comma-separated amount is fragmented by layout analysis.", s["BodyText"]),
        Paragraph("Owner: Finance Data Office", s["BodyText"]),
    ]
    build_pdf(OUTPUT_DIR / "complex_financial_report.pdf", "Complex Financial Report Fixture", story)


def standard_contract() -> None:
    s = styles()
    clause_rows = [
        ["Clause", "Requirement", "Evidence Field"],
        ["2.1", "Supplier must keep trace logs for every parsing run.", "trace_path"],
        ["2.2", "Output JSON must include structured sections and tables.", "result.json"],
        ["3.1", "Failures must be recoverable without stopping the batch.", "batch_report.json"],
        ["4.1", "Keys and tokens must not be written to public artifacts.", "secret_scan"],
    ]
    story: list[object] = [
        Paragraph("Data Processing Service Agreement", s["Title"]),
        Paragraph("Contract No: STD-2026-MINERU-07", s["BodyText"]),
        Paragraph("Effective Date: 2026-05-20", s["BodyText"]),
        Paragraph("Parties: Corpus Producer A and Processing Vendor B", s["BodyText"]),
        Spacer(1, 8),
        Paragraph("1. Scope", s["Heading1"]),
        Paragraph(
            "The vendor provides a traceable document parsing agent for PDF, scanned files, web pages, and structured exports.",
            s["BodyText"],
        ),
        Paragraph("2. Compliance Clauses", s["Heading1"]),
        table(clause_rows),
        PageBreak(),
        Paragraph("3. Service Level", s["Heading1"]),
        Paragraph("Batch tasks must continue after a single item failure and must record the error message.", s["BodyText"]),
        Paragraph("4. Exception Handling", s["Heading1"]),
        Paragraph("Risk: missing page provenance must be reported as a quality issue instead of being hidden.", s["BodyText"]),
        Paragraph("Recommendation: the reviewer should inspect trace.json and retrieval_quality.json.", s["BodyText"]),
        Paragraph("5. Signature", s["Heading1"]),
        Paragraph("Signed by: Data Governance Office / Vendor Engineering Lead", s["BodyText"]),
    ]
    build_pdf(OUTPUT_DIR / "standard_contract_cross_page.pdf", "Data Processing Service Agreement", story)


def workflow_report() -> None:
    s = styles()
    metrics = [
        ["Step", "Input", "Tool", "Expected Output", "Recovery Rule"],
        ["1", "PDF upload", "API layer", "stored file", "reject oversize input"],
        ["2", "document", "MinerU CLI", "markdown and content list", "retry online API"],
        ["3", "content blocks", "validator", "quality report", "mark needs_review"],
        ["4", "markdown", "retrieval exporter", "jsonl chunks", "skip noisy blocks"],
    ]
    story: list[object] = [
        Paragraph("Engineering Workflow Inspection Report", s["Title"]),
        Paragraph("Inspection Date: 2026-05-22", s["BodyText"]),
        Paragraph("System: MinerU Data Agent processing line", s["BodyText"]),
        Spacer(1, 8),
        Paragraph("1. Workflow Diagram", s["Heading1"]),
        FlowChart(),
        Paragraph("2. Execution Matrix", s["Heading1"]),
        table(metrics),
        PageBreak(),
        Paragraph("3. Findings", s["Heading1"]),
        Paragraph("Anomaly: a previous API smoke sample was too short and triggered a quality warning.", s["BodyText"]),
        Paragraph("Recommendation: use richer smoke inputs and keep warnings visible in the result.", s["BodyText"]),
        Paragraph("4. Review Targets", s["Heading1"]),
        Paragraph("Check that every run has result.json, trace.json, summary.md, and retrieval artifacts.", s["BodyText"]),
    ]
    build_pdf(OUTPUT_DIR / "workflow_diagram_report.pdf", "Engineering Workflow Inspection Report", story)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    financial_report()
    standard_contract()
    workflow_report()
    readme = """# Real PDF Fixtures

These PDFs are file-level evaluation fixtures for the competition submission.
They contain synthetic business content so they can be shared publicly without
copyright or privacy risk. They are used to generate MinerU CLI evidence under
`submission_artifacts/mineru_cases/`.
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
