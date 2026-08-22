#!/usr/bin/env python3
"""make_charts — regenerate the README benchmark charts from the benchmark data.

The charts in the README are computed, not hand-drawn. This reads the same sources
the tables do — replication.json for the pooled best-picks, the raw method outputs
re-scored by the current detector for the register panel, and the search-informed
regression and rewrite results, plus the version-pinned competitor capability audit.
It draws six bar charts and one capability matrix in assets/ and writes a small
chart-data.json manifest.

    python3 bench/make_charts.py            # regenerate the PNGs and the manifest
    python3 bench/make_charts.py --check    # fail if the data drifted (CI)

--check recomputes the numbers from the data and compares them to the committed
manifest, so a benchmark re-run or a scorer change that would move a bar fails the
build until the charts are regenerated. It compares the data, not the PNG bytes,
so it does not depend on the Pillow or font version.

Rendering needs Pillow and a system sans font; the --check data comparison does
not, so CI can verify freshness even where Pillow is absent.
"""
import json
import sys
import statistics as st
from io import BytesIO
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
ASSETS = ROOT / "assets"
MANIFEST = BENCH / "chart-data.json"
SEARCH_RESULTS = BENCH / "search-corpus" / "results.json"
CAPABILITY_AUDIT = BENCH / "competitor-capabilities.json"
SEARCH_COMPARISON = BENCH / "search-corpus" / "comparison-results.json"
sys.path.insert(0, str(ROOT / "scripts"))
from safeio import atomic_write_bytes, atomic_write_text  # noqa: E402

# Where each method's rewrites live, and the label shown on the chart. The panel
# re-scores these with the live detector, so the numbers track the current meter.
PANEL = [
    ("original drafts", None),
    ("isatimur/de-slop", ["deslop_h1.json", "deslop_h2.json"]),
    ("stacked pipeline", ["anthpipe_h1.json", "anthpipe_h2.json"]),
    ("blader/humanizer", ["blader_h1.json", "blader_h2.json"]),
    ("petergyang/no-ai-slop", ["petergyang_h1.json", "petergyang_h2.json"]),
    ("hardikpandya/stop-slop", ["stopslop_h1.json", "stopslop_h2.json"]),
    ("Zero Slop", ["zeroslop12_h1.json", "zeroslop12_h2.json"]),
]
BEST_LABELS = {"zeroslop": "Zero Slop", "blader": "blader/humanizer",
               "petergyang": "petergyang/no-ai-slop", "deslop": "isatimur/de-slop"}


def compute():
    """Return the five chart datasets, computed from the benchmark data."""
    import slopscore
    data = slopscore.load_patterns()

    # 1. best-picks, pooled across both replication runs
    rep = json.loads((BENCH / "replication.json").read_text())
    pooled = {}
    for run in ("run1", "run2"):
        for m, n in rep[run].items():
            pooled[m] = pooled.get(m, 0) + n
    best = [(BEST_LABELS.get(m, m), pooled[m]) for m in
            sorted(pooled, key=lambda m: -pooled[m])]

    # 2. register panel, re-scored by the current detector
    ex = json.loads((BENCH / "examples.json").read_text())
    panel = []
    for label, files in PANEL:
        if files is None:
            scores = [slopscore.score_text(e["draft"], data)["ai_likelihood"] for e in ex]
        else:
            docs = {}
            for f in files:
                p = BENCH / "outputs" / f
                if not p.exists():
                    raise ValueError(f"missing benchmark output: {p}")
                part = json.loads(p.read_text())
                overlap = set(docs) & set(part)
                if overlap:
                    raise ValueError(f"duplicate benchmark ids in {p.name}: {sorted(overlap)}")
                docs.update(part)
            expected = {row["id"] for row in ex}
            if set(docs) != expected:
                raise ValueError(f"{label}: output ids do not match examples.json")
            scores = [slopscore.score_text(docs[row["id"]], data)["ai_likelihood"]
                      for row in ex]
        panel.append((label, round(st.mean(scores), 1)))
    search = json.loads(SEARCH_RESULTS.read_text())
    search_panel = [
        (genre, row["mean_surface_score"])
        for genre, row in sorted(search["by_genre"].items())
    ]
    audit = json.loads(CAPABILITY_AUDIT.read_text())
    products = ["zero_slop", "blader", "no_ai_slop"]
    capability_matrix = {
        "audited_on": audit["audited_on"],
        "products": [
            [key, audit["products"][key]["label"], audit["products"][key]["commit"]]
            for key in products
        ],
        "rows": [
            [row["label"], *[row[key] for key in products]]
            for row in audit["capabilities"]
        ],
    }
    comparison = json.loads(SEARCH_COMPARISON.read_text())
    comparison_order = ["zero-slop", "no-ai-slop", "humanizer",
                        "de-slop", "stop-slop"]
    rewrite_scores = [("Original drafts",
                       comparison["original_mean_surface_score"])]
    rewrite_scores.extend(
        (comparison["methods"][method]["label"],
         comparison["methods"][method]["mean_surface_score"])
        for method in comparison_order
    )
    rewrite_passes = [("Original drafts",
                       comparison["original_combined_pass_rate"])]
    rewrite_passes.extend(
        (comparison["methods"][method]["label"],
         comparison["methods"][method]["combined_pass_rate"])
        for method in comparison_order
    )
    external_order = ["original", *comparison_order]
    external_clean = [
        (comparison["external_cross_meter"]["methods"][method]["label"],
         comparison["external_cross_meter"]["methods"][method]["reads_clean_rate"])
        for method in external_order
    ]
    return {"best_picks": best, "detector_panel": panel,
            "search_corpus": search_panel,
            "search_rewrite_scores": rewrite_scores,
            "search_rewrite_passes": rewrite_passes,
            "external_checker_clean": external_clean,
            "capability_matrix": capability_matrix}


# ---- rendering (Pillow) --------------------------------------------------
FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
INK, MUTE, GRID = (27, 29, 34), (91, 98, 112), (226, 229, 233)
BRAND, MUTEDBAR = (42, 120, 214), (176, 188, 204)


def _font(size, bold=False):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=1 if bold and path.endswith(".ttc") else 0)
            except Exception:
                continue
    return ImageFont.load_default()


def _hbar(path, title, subtitle, rows, ours_label):
    from PIL import Image, ImageDraw
    W, padL, padR, top, rowh = 1240, 340, 90, 96, 52
    H = top + len(rows) * rowh + 70
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((44, 30), title, font=_font(27, True), fill=INK)
    d.text((44, 66), subtitle, font=_font(15), fill=MUTE)
    vmax = (max(v for _, v in rows) * 1.16) or 1
    x0, x1 = padL, W - padR
    for i in range(5):
        gx = x0 + (x1 - x0) * i / 4
        d.line([(gx, top - 6), (gx, H - 46)], fill=GRID, width=1)
        d.text((gx - 8, H - 40), f"{vmax * i / 4:.0f}", font=_font(12), fill=MUTE)
    for i, (label, val) in enumerate(rows):
        y = top + i * rowh
        ours = ours_label is None or label == ours_label
        d.text((x0 - 16, y + rowh // 2 - 9), label, font=_font(15, ours),
               fill=INK if ours else MUTE, anchor="ra")
        bw = (x1 - x0) * val / vmax
        col = BRAND if ours else MUTEDBAR
        d.rounded_rectangle([x0, y + 8, x0 + max(bw, 3), y + rowh - 14], 4, fill=col)
        d.text((x0 + bw + 10, y + rowh // 2 - 10), f"{val:g}", font=_font(15, True),
               fill=col if ours else MUTE)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    atomic_write_bytes(path, buffer.getvalue())
    return path.name


def _capability_matrix(path, audit):
    """Render a presence matrix without turning capabilities into a quality score."""
    from PIL import Image, ImageDraw
    W, left, top, rowh = 1240, 620, 168, 43
    products = audit["products"]
    rows = audit["rows"]
    centers = [750, 940, 1120]
    H = top + len(rows) * rowh + 112
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((44, 28), "Documented editorial system capabilities",
           font=_font(27, True), fill=INK)
    d.text((44, 66), "Repository audit at pinned commits. Presence is not effectiveness proof.",
           font=_font(15), fill=MUTE)
    d.text((44, 96), "Native = dedicated component or named gate. Guided = instruction or self-check.",
           font=_font(13), fill=MUTE)

    for x, (_, label, commit) in zip(centers, products):
        d.text((x, 125), label, font=_font(13, label == "Zero Slop"),
               fill=INK if label == "Zero Slop" else MUTE, anchor="ma")
        d.text((x, 145), commit[:8], font=_font(10), fill=MUTE, anchor="ma")

    for i, row in enumerate(rows):
        y = top + i * rowh
        if i % 2 == 0:
            d.rounded_rectangle([32, y, W - 32, y + rowh - 2], 5,
                                fill=(247, 248, 250))
        d.text((44, y + rowh // 2), row[0], font=_font(14), fill=INK, anchor="lm")
        for x, status in zip(centers, row[1:]):
            cy, r = y + rowh // 2, 8
            if status == "native":
                d.ellipse([x - r, cy - r, x + r, cy + r], fill=BRAND)
            elif status == "guided":
                d.pieslice([x - r, cy - r, x + r, cy + r], 90, 270,
                           fill=(230, 168, 63))
                d.ellipse([x - r, cy - r, x + r, cy + r], outline=(184, 136, 48), width=2)
            else:
                d.ellipse([x - r, cy - r, x + r, cy + r], outline=MUTEDBAR, width=2)

    legend_y = top + len(rows) * rowh + 34
    legend = [
        (BRAND, "Native"),
        ((230, 168, 63), "Guided"),
        (None, "Not documented"),
    ]
    x = 44
    for color, label in legend:
        if color:
            d.ellipse([x, legend_y - 7, x + 14, legend_y + 7], fill=color)
        else:
            d.ellipse([x, legend_y - 7, x + 14, legend_y + 7], outline=MUTEDBAR, width=2)
        d.text((x + 24, legend_y), label, font=_font(12), fill=MUTE, anchor="lm")
        x += 132 if label != "Not documented" else 190
    d.text((W - 44, legend_y), f"Audited {audit['audited_on']}",
           font=_font(11), fill=MUTE, anchor="rm")
    img.save(path)
    return path.name


def render(datasets):
    ASSETS.mkdir(exist_ok=True)
    out = []
    out.append(_hbar(
        ASSETS / "bench-bestpicks.png",
        "Blind LLM-as-a-judge selections",
        "50 synthetic drafts; five judge runs per pass; no human raters. Higher is better.",
        datasets["best_picks"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-detector.png",
        "AI register remaining after de-slop",
        "Detector score, lower means more of the AI accent removed. Scored by Zero Slop's own "
        "meter, so read it as register stripped, not an independent verdict.",
        datasets["detector_panel"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-search-corpus.png",
        "Search-informed slop challenge",
        "18 anonymous paraphrases, three per genre. Higher means more tracked surface slop; "
        "this is a regression check, not field accuracy.",
        datasets["search_corpus"], None))
    out.append(_hbar(
        ASSETS / "bench-search-rewrites.png",
        "Surface score after instruction replay",
        "Same 18 paraphrases and one host model. Lower is cleaner. Zero Slop's meter, "
        "not an independent judge.",
        datasets["search_rewrite_scores"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-search-passrate.png",
        "Clean-and-fact-checked pass rate",
        "Genre score gate plus automated fact check. Not semantic or field accuracy.",
        datasets["search_rewrite_passes"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-external-checker.png",
        "Reads-clean rate on the public AIStoryHub checker",
        "Corpus v1.8; item-level browser checks; eligible items only (20-word minimum). "
        "Higher is better; 0-4 abstentions per method.",
        datasets["external_checker_clean"], "Zero Slop"))
    out.append(_capability_matrix(
        ASSETS / "competitor-capabilities.png",
        datasets["capability_matrix"]))
    return out


def main():
    check = "--check" in sys.argv
    fresh = compute()
    if check:
        if not MANIFEST.exists():
            print("chart-data.json missing — run: python3 bench/make_charts.py")
            return 1
        stored = json.loads(MANIFEST.read_text())
        # normalise (json turns tuples into lists)
        norm = json.loads(json.dumps(fresh))
        if stored != norm:
            print("benchmark charts are out of date — the data moved.")
            print("  run: python3 bench/make_charts.py")
            return 1
        print("benchmark charts are current")
        return 0
    names = render(fresh)
    atomic_write_text(MANIFEST, json.dumps(fresh, indent=1) + "\n")
    print(f"wrote {', '.join(names)} and {MANIFEST.name} from the benchmark data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
