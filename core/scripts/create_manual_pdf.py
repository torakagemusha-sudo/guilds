from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle

from core.scripts.pdf_generator import build_styles, generate_pdf


MERMAID = """flowchart TD
A[.guilds Spec] --> B[Parser]
B --> C[Typed Program Model]
C --> D[Evaluator]
D --> E[Surface Model]
E --> F[Render Tree Builder]
F --> G[HTML / Desktop Renderers]
C --> H[Exporters]
H --> I[JSON / React / State Machines]"""


def build_story():
    styles = build_styles()
    story = []

    # Page 1: Cover
    story.append(Spacer(1, 65))
    story.append(Paragraph("GUILDS Manual", styles["DocumentTitle"]))
    story.append(Paragraph("A concise 4-page reference for the architecture and workflow", styles["ReportSubtitle"]))
    story.append(Spacer(1, 18))
    story.append(
        Paragraph(
            "<b>What this manual covers:</b><br/>"
            "Core concepts, system architecture, the standard build loop, and primary reference points.",
            styles["CalloutBox"],
        )
    )
    story.append(Spacer(1, 24))
    story.append(
        Paragraph(
            "GUILDS is a specification-driven interface toolkit built around claims, affordances, vessels, stages, and flows. "
            "It is designed for trustworthy internal tools where visibility, recovery, and phase-aware interaction matter.",
            styles["BodyJustified"],
        )
    )
    story.append(PageBreak())

    # Page 2: TOC + overview
    story.append(Paragraph("Table of Contents", styles["TOCHeading"]))
    toc_rows = [
        ["Section", "Page"],
        ["1. Cover", "1"],
        ["2. Contents and Overview", "2"],
        ["3. Architecture Diagram", "3"],
        ["4. Workflow and References", "4"],
    ]
    table = Table(toc_rows, colWidths=[120 * mm, 25 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498DB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 18))
    story.append(Paragraph("Overview", styles["Heading2Custom"]))
    story.append(
        Paragraph(
            "GUILDS turns a single `.guilds` specification into multiple render targets while preserving the same interaction model. "
            "The language emphasizes cognitive clarity by making state, trust, recovery, and user action explicit.",
            styles["BodyJustified"],
        )
    )
    story.append(
        Paragraph(
            "The primary building blocks are `claim`, `afford`, `vessel`, `stage`, and `flow`. "
            "Together they let developers design UI behavior as a structured surface instead of a loose collection of widgets.",
            styles["BodyJustified"],
        )
    )
    story.append(PageBreak())

    # Page 3: Architecture diagram
    story.append(Paragraph("Architecture Diagram", styles["Heading1Custom"]))
    story.append(
        Paragraph(
            "The evaluator owns meaning; renderers and exporters only project that resolved model.",
            styles["BodyJustified"],
        )
    )
    diagram_rows = [
        ["Layer", "Responsibility"],
        [".guilds Spec", "Declarative source"],
        ["Parser", "Typed program model"],
        ["Evaluator", "Phase and visibility resolution"],
        ["Renderers / Exporters", "Target outputs"],
    ]
    diagram_table = Table(diagram_rows, colWidths=[45 * mm, 115 * mm])
    diagram_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#D0D7DE")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(diagram_table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Mermaid Source", styles["Heading2Custom"]))
    story.append(Paragraph(f"<pre>{MERMAID}</pre>", styles["CodeBlock"]))
    story.append(PageBreak())

    # Page 4: Workflow + references
    story.append(Paragraph("Workflow", styles["Heading1Custom"]))
    workflow = [
        "1. Validate with `guilds validate myapp.guilds`.",
        "2. Build HTML first with `guilds build myapp.guilds`.",
        "3. Inspect phase snapshots with `guilds render myapp.guilds idle` and related phases.",
        "4. Move to desktop backends such as `pyside6` after the stage model is stable.",
        "5. Generate docs with `guilds pdf` when you need formatted manuals.",
    ]
    for line in workflow:
        story.append(Paragraph(line, styles["BulletItem"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("References", styles["Heading2Custom"]))
    refs = [
        "docs/USER_GUIDE.md",
        "docs/GUILDS_v2_ASCII_Encoded.md",
        "core/README.md",
        "core/guilds_parser.py",
        "core/guilds_evaluator.py",
        "core/guilds_cli.py",
    ]
    for ref in refs:
        story.append(Paragraph(f"• {ref}", styles["BulletItem"]))

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "This manual is intentionally brief. The language specification remains the authoritative source for grammar and system constraints.",
            styles["BodyJustified"],
        )
    )

    return story


def main():
    output = Path("outputs") / "guilds_manual.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_pdf(build_story(), str(output))
    print(output)


if __name__ == "__main__":
    main()
