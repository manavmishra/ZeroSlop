#!/usr/bin/env python3
"""Render ONE-PAGER.md to a styled PDF for sharing or download.

Keeps the PDF in step with the markdown so the two never drift: it parses
ONE-PAGER.md (headings, paragraphs, the demo image, the install command, the
footer) and lays it out with reportlab in the project's brand colour. Re-run it
whenever the one-pager changes.

    python3 scripts/build_onepager_pdf.py           # rebuild
    python3 scripts/build_onepager_pdf.py --check   # fail if stale (CI)

Needs reportlab (the only script here that does); everything user-facing stays
stdlib-only. If reportlab is missing it says so and exits cleanly.
"""
import argparse
import io
import re
import sys
from pathlib import Path
from safeio import atomic_write_bytes, is_within

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "ONE-PAGER.md"
OUT = ROOT / "assets" / "Zero-Slop-One-Pager.pdf"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        from reportlab import rl_config
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Image, HRFlowable, Preformatted)
    except ImportError:
        print("reportlab not installed; run: pip install reportlab")
        return 1

    # ReportLab otherwise embeds the current time in the document metadata.
    # Invariant mode makes the PDF byte-reproducible, so CI can detect drift.
    rl_config.invariant = 1

    BRAND = colors.HexColor("#2B5BC7")
    INK = colors.HexColor("#1B1D22")
    MUTE = colors.HexColor("#5B6270")
    PANEL = colors.HexColor("#F2F5FA")

    H1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=27, leading=30,
                        textColor=INK, alignment=TA_LEFT, spaceAfter=2)
    H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13, leading=16,
                        textColor=BRAND, spaceBefore=13, spaceAfter=5)
    BODY = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.4, leading=13.4,
                          textColor=INK, spaceAfter=7)
    CODE = ParagraphStyle("Code", fontName="Courier", fontSize=9, leading=12,
                          textColor=INK, backColor=PANEL, borderPadding=(6, 6, 6, 6),
                          spaceBefore=2, spaceAfter=8)
    FOOT = ParagraphStyle("Foot", fontName="Helvetica", fontSize=8, leading=11,
                          textColor=MUTE)

    def inline(t):
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
        t = re.sub(r"`(.+?)`", r'<font face="Courier" size="8.5">\1</font>', t)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<font color="#2B5BC7">\1</font>', t)
        return t

    story, para, code, in_footer, in_code = [], [], [], False, False

    def flush_para():
        if para:
            story.append(Paragraph(" ".join(para), FOOT if in_footer else BODY))
            para.clear()

    if not SRC.is_file() or SRC.is_symlink():
        print(f"missing or unsafe source: {SRC}", file=sys.stderr)
        return 1
    try:
        source_lines = SRC.read_text().splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"cannot read {SRC}: {exc}", file=sys.stderr)
        return 1

    for line in source_lines:
        s = line.strip()
        if s.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code), CODE)); code.clear()
            else:
                flush_para()
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        if s == "---":
            flush_para()
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", color=colors.HexColor("#D9DEE6"), thickness=0.6))
            story.append(Spacer(1, 5))
            in_footer = True
            continue
        if s.startswith("!["):
            flush_para()
            m = re.search(r"\(([^)]+)\)", s)
            raw_img = ROOT / m.group(1) if m else None
            img = raw_img.resolve() if raw_img else None
            if (not img or not is_within(img, ROOT) or not img.is_file()
                    or raw_img.is_symlink()):
                print(f"invalid or missing one-pager image: {s}", file=sys.stderr)
                return 1
            iw, ih = ImageReader(str(img)).getSize()
            w = 5.3 * inch
            story.append(Spacer(1, 3))
            story.append(Image(str(img), width=w, height=w * ih / iw))
            story.append(Spacer(1, 7))
            continue
        if s.startswith("# "):
            flush_para(); story.append(Paragraph(inline(s[2:]), H1)); continue
        if s.startswith("## "):
            flush_para(); story.append(Paragraph(inline(s[3:]), H2)); continue
        if not s:
            flush_para(); continue
        para.append(inline(s))
    if in_code:
        print("ONE-PAGER.md has an unclosed code fence", file=sys.stderr)
        return 1
    flush_para()

    buffer = io.BytesIO()
    try:
        SimpleDocTemplate(
            buffer, pagesize=letter, title="Zero Slop - One-Pager",
            author="Manav Mishra", leftMargin=0.85 * inch, rightMargin=0.85 * inch,
            topMargin=0.7 * inch, bottomMargin=0.6 * inch,
        ).build(story)
        pdf = buffer.getvalue()
        if not pdf.startswith(b"%PDF-"):
            raise ValueError("renderer did not produce a PDF")
        if args.check:
            if not OUT.is_file() or OUT.is_symlink() or OUT.read_bytes() != pdf:
                print("one-pager PDF is out of date — run: "
                      "python3 scripts/build_onepager_pdf.py")
                return 1
        else:
            atomic_write_bytes(OUT, pdf)
    except (OSError, ValueError) as exc:
        print(f"cannot build one-pager PDF: {exc}", file=sys.stderr)
        return 1
    if args.check:
        print("one-pager PDF is current")
    else:
        print(f"wrote {OUT.relative_to(ROOT)} ({len(pdf):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
