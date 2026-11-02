#!/usr/bin/env python3
"""Build the report and one-page revision PDF from their Markdown sources."""
from __future__ import annotations

import html
import re
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
GREEN = colors.HexColor("#164d3d")
INK = colors.HexColor("#24352f")
MUTED = colors.HexColor("#64756e")


def register_fonts() -> None:
    """Prefer Unicode fonts when present; ReportLab's bundled Vera is portable."""
    candidates = [Path("/usr/share/fonts/truetype/dejavu")]
    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
    candidates += list(runtime.glob("native/libreoffice-headless/**/fonts/truetype"))
    base = next((p for p in candidates if (p / "DejaVuSans.ttf").exists()), None)
    if base:
        regular, bold, mono = (base / p for p in
                              ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansMono.ttf"))
    else:
        base = Path(reportlab.__file__).parent / "fonts"
        regular, bold, mono = (base / p for p in ("Vera.ttf", "VeraBd.ttf", "Vera.ttf"))
    for name, path in (("Navic", regular), ("NavicBold", bold), ("NavicMono", mono)):
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily("Navic", normal="Navic", bold="NavicBold")


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font name="NavicMono">\1</font>', text)
    return text


def styles(compact: bool = False) -> dict[str, ParagraphStyle]:
    size, lead = (8.1, 10.6) if compact else (9.5, 13.5)
    body = ParagraphStyle("body", fontName="Navic", fontSize=size, leading=lead,
                          textColor=INK, spaceAfter=7,
                          alignment=TA_LEFT, splitLongWords=True)
    return {
        "body": body,
        "h1": ParagraphStyle("h1", parent=body, fontName="NavicBold",
                             fontSize=17 if compact else 23, leading=22 if compact else 29,
                             textColor=GREEN, spaceAfter=13, keepWithNext=True),
        "h2": ParagraphStyle("h2", parent=body, fontName="NavicBold", fontSize=12.2,
                             leading=17, textColor=GREEN, spaceBefore=7, spaceAfter=7,
                             keepWithNext=True),
        "cell": ParagraphStyle("cell", parent=body, fontSize=8.3, leading=11.6, spaceAfter=0),
        "code": ParagraphStyle("code", parent=body, fontName="NavicMono", fontSize=7.7,
                               leading=11, backColor=colors.HexColor("#edf3ef"),
                               borderPadding=8, spaceAfter=12),
        "caption": ParagraphStyle("caption", parent=body, fontSize=8, leading=11,
                                  textColor=MUTED, spaceAfter=10),
    }


def markdown_flowables(path: Path, width: float, compact: bool = False) -> list:
    """Render only the deliberate, small Markdown subset used by these sources."""
    sheet = styles(compact)
    lines = path.read_text(encoding="utf-8").splitlines()
    flow: list = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line == "---":
            flow.append(PageBreak())
        elif line.startswith("```"):
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(html.escape(lines[i]).replace(" ", "&#160;"))
                i += 1
            i += 1
            flow.append(Paragraph("<br/>".join(code), sheet["code"]))
        elif line.startswith("!["):
            match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
            if not match:
                raise ValueError(f"Invalid image: {line}")
            img = Image(str(path.parent / match[2]))
            max_height = 225 if "mobile" in match[2] else 315
            scale = min(width / img.imageWidth, max_height / img.imageHeight)
            img.drawWidth, img.drawHeight = img.imageWidth * scale, img.imageHeight * scale
            img.hAlign = "CENTER"
            flow += [Spacer(1, 6), img, Spacer(1, 5), Paragraph(inline(match[1]), sheet["caption"])]
        elif line.startswith("|"):
            rows = [line]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = [[c.strip() for c in row.strip("|").split("|")] for row in rows]
            cells = [row for row in cells if not all(re.fullmatch(r"[-:]+", c) for c in row)]
            ncols = len(cells[0])
            # Three-column results tables need more room for the scenario text.
            proportions = [1 / ncols] * ncols
            if ncols == 2:
                proportions = [0.31, 0.69]
            elif ncols == 3:
                proportions = [0.37, 0.32, 0.31]
            formatted = [[Paragraph(("<b>" if r == 0 else "") + inline(c) +
                                    ("</b>" if r == 0 else ""), sheet["cell"])
                          for c in row] for r, row in enumerate(cells)]
            table = Table(formatted, colWidths=[width * p for p in proportions], repeatRows=1)
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfece4")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7f5")]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#bed2c5")),
            ]))
            flow += [table, Spacer(1, 10)]
        elif line.startswith("# "):
            flow.append(Paragraph(inline(line[2:]), sheet["h1"]))
        elif line.startswith("## "):
            flow.append(Paragraph(inline(line[3:]), sheet["h2"]))
        else:
            if line.startswith("- "):
                line = "• " + line[2:]
            flow.append(Paragraph(inline(line), sheet["body"]))
    return flow


def footer(canvas, doc) -> None:
    canvas.saveState()
    w, _ = A4
    canvas.setStrokeColor(colors.HexColor("#c9d9cf"))
    canvas.line(doc.leftMargin, 33, w - doc.rightMargin, 33)
    canvas.setFont("Navic", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 21, "NAVIC  /  NSUT MINOR PROJECT  /  02 NOV 2026")
    canvas.drawRightString(w - doc.rightMargin, 21, str(doc.page))
    canvas.restoreState()


def build(source: str, filename: str, compact: bool = False) -> None:
    margin = 34 if compact else 43
    doc = SimpleDocTemplate(str(OUT / filename), pagesize=A4, leftMargin=margin,
                            rightMargin=margin, topMargin=30 if compact else 40,
                            bottomMargin=45, title="Navic — " + ("Viva cheat sheet" if compact else "Minor project report"),
                            author="Navic project", pageCompression=1)
    content = markdown_flowables(ROOT / "docs" / source, doc.width, compact)
    doc.build(content, onFirstPage=footer, onLaterPages=footer)
    print(OUT / filename)


if __name__ == "__main__":
    register_fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    build("report.md", "navic-minor-project-report.pdf")
    build("cheat-sheet.md", "navic-viva-cheat-sheet.pdf", compact=True)
