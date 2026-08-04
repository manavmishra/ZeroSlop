#!/usr/bin/env python3
"""make_charts — regenerate the README benchmark charts from the benchmark data.

The charts in the README are computed, not hand-drawn. This reads the same sources
the tables do — replication.json for the pooled best-picks, and the raw method
outputs re-scored by the current detector for the register panel — draws two bar
charts, and writes them to assets/ alongside a small chart-data.json manifest.

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
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
ASSETS = ROOT / "assets"
MANIFEST = BENCH / "chart-data.json"
sys.path.insert(0, str(ROOT / "scripts"))

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
    """Return the two chart datasets, computed from the benchmark data."""
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
                if p.exists():
                    docs.update(json.loads(p.read_text()))
            scores = [slopscore.score_text(t, data)["ai_likelihood"] for t in docs.values()]
        panel.append((label, round(st.mean(scores), 1)))
    return {"best_picks": best, "detector_panel": panel}


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
        ours = label == ours_label
        d.text((x0 - 16, y + rowh // 2 - 9), label, font=_font(15, ours),
               fill=INK if ours else MUTE, anchor="ra")
        bw = (x1 - x0) * val / vmax
        col = BRAND if ours else MUTEDBAR
        d.rounded_rectangle([x0, y + 8, x0 + max(bw, 3), y + rowh - 14], 4, fill=col)
        d.text((x0 + bw + 10, y + rowh // 2 - 10), f"{val:g}", font=_font(15, True),
               fill=col if ours else MUTE)
    img.save(path)
    return path.name


def render(datasets):
    ASSETS.mkdir(exist_ok=True)
    out = []
    out.append(_hbar(
        ASSETS / "bench-bestpicks.png",
        "Best-picks, pooled over 100 blind verdicts",
        "50 AI-typical drafts, six genres, judges blind on shuffled labels. Higher is better.",
        datasets["best_picks"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-detector.png",
        "AI register remaining after de-slop",
        "Detector score, lower means more of the AI accent removed. Scored by Zero Slop's own "
        "meter, so read it as register stripped, not an independent verdict.",
        datasets["detector_panel"], "Zero Slop"))
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
        if stored.get("best_picks") != norm["best_picks"] or \
           stored.get("detector_panel") != norm["detector_panel"]:
            print("benchmark charts are out of date — the data moved.")
            print("  run: python3 bench/make_charts.py")
            return 1
        print("benchmark charts are current")
        return 0
    names = render(fresh)
    MANIFEST.write_text(json.dumps(fresh, indent=1) + "\n")
    print(f"wrote {', '.join(names)} and {MANIFEST.name} from the benchmark data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
