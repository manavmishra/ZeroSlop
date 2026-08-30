#!/usr/bin/env python3
"""make_charts — regenerate the README benchmark charts from the benchmark data.

The charts in the README are computed, not hand-drawn. This reads the same sources
the tables do: the current-model RAID+ audit, raw method outputs re-scored by the
current detector, search-informed regression and rewrite results, external research
audits, and the version-pinned competitor capability audit. It writes the chart PNGs
and a small chart-data.json manifest.

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
FRESH_REPLAY = BENCH / "fresh-replay" / "results.json"
INCUMBENT_BLIND_REPLAY = BENCH / "incumbent-blind-replay" / "results.json"
EXTERNAL_MODELS = BENCH / "external-models" / "results.json"
BEEMO_RESULTS = BENCH / "beemo-corpus" / "results.json"
RAID_PLUS_RESULTS = BENCH / "raid-plus-corpus" / "results.json"
QUALITY_RESULTS = BENCH / "quality-corpus" / "results.json"
FEATURE_ABLATION = BENCH / "feature-ablation" / "results.json"
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
def compute():
    """Return chart datasets computed from the benchmark data."""
    import slopscore
    data = slopscore.load_patterns()

    # Preserved output panels are always re-scored by the current detector.
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
    # Derived from the audit rather than listed here: two products were added to
    # competitor-capabilities.json and silently did not render, because this list
    # was the real source of truth for the chart. Zero Slop stays first as the
    # subject of the comparison; the rest follow the audit's own order.
    products = ["zero_slop"] + [k for k in audit["products"] if k != "zero_slop"]
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
    fresh_replay = json.loads(FRESH_REPLAY.read_text())
    if (fresh_replay.get("result_kind") != "fresh_same_model_rewrite_replay"
            or fresh_replay.get("calibrated_field_accuracy") is not False
            or fresh_replay.get("corpus", {}).get("drafts") != 18):
        raise ValueError("fresh same-model replay has an invalid contract")
    replay_order = ["zero-slop", "avoid-ai-writing", "no-ai-slop", "humanizer"]
    rewrite_scores = [(fresh_replay["originals"]["label"],
                       fresh_replay["originals"]["mean_writing_score"])]
    rewrite_scores.extend(
        (fresh_replay["methods"][method]["label"],
         fresh_replay["methods"][method]["mean_writing_score"])
        for method in replay_order
    )
    rewrite_passes = [(fresh_replay["originals"]["label"],
                       round(100 * fresh_replay["originals"]["zero_slop_release_passes"]
                             / fresh_replay["corpus"]["drafts"], 1))]
    rewrite_passes.extend(
        (fresh_replay["methods"][method]["label"],
         round(100 * fresh_replay["methods"][method]["zero_slop_release_passes"]
               / fresh_replay["corpus"]["drafts"], 1))
        for method in replay_order
    )
    incumbent_replay = json.loads(INCUMBENT_BLIND_REPLAY.read_text())
    review = incumbent_replay.get("editorial_review", {})
    if (incumbent_replay.get("result_kind")
            != "fresh_method_hidden_incumbent_rewrite_comparison"
            or incumbent_replay.get("calibrated_field_accuracy") is not False
            or incumbent_replay.get("corpus", {}).get("drafts") != 18
            or review.get("method_hidden") is not True):
        raise ValueError("method-hidden incumbent replay has an invalid contract")
    consensus = review["consensus"]
    incumbent_hidden_preferences = [
        (incumbent_replay["methods"]["zero-slop"]["label"], consensus["zero-slop"]),
        (incumbent_replay["methods"]["avoid-ai-writing"]["label"],
         consensus["avoid-ai-writing"]),
        ("Tie", consensus["tie"]),
        ("Unresolved", consensus["unresolved"]),
    ]
    comparison_order = ["zero-slop", "no-ai-slop", "humanizer",
                        "de-slop", "stop-slop"]
    external_order = ["original", *comparison_order]
    external_clean = [
        (comparison["external_cross_meter"]["methods"][method]["label"],
         comparison["external_cross_meter"]["methods"][method]["reads_clean_rate"])
        for method in external_order
    ]
    external_models = json.loads(EXTERNAL_MODELS.read_text())
    source = external_models.get("source", {})
    models = external_models.get("models", [])
    if (external_models.get("result_kind") != "external_reproduction"
            or not isinstance(source.get("commit"), str)
            or len(source["commit"]) != 40
            or len(models) != external_models.get("sample", {}).get("models")
            or len({row.get("model") for row in models}) != len(models)):
        raise ValueError("external model reproduction has an invalid contract")
    if [row.get("rank") for row in models] != list(range(1, len(models) + 1)):
        raise ValueError("external model rows must be ordered by published rank")
    model_context = [(row["model"], row["overall"]) for row in models]
    beemo = json.loads(BEEMO_RESULTS.read_text())
    if (beemo.get("result_kind") != "external_paired_edit_surface_audit"
            or beemo.get("calibrated_accuracy") is not False
            or beemo.get("source", {}).get("rows") != 2187):
        raise ValueError("Beemo paired-edit audit has an invalid contract")
    beemo_surface = [
        (beemo["groups"][field]["label"],
         beemo["groups"][field]["mean_surface_score"])
        for field in ("model_output", "human_edits", "human_output")
    ]
    raid_plus = json.loads(RAID_PLUS_RESULTS.read_text())
    if (raid_plus.get("result_kind") != "current_model_surface_audit"
            or raid_plus.get("calibrated_accuracy") is not False
            or raid_plus.get("source", {}).get("rows") != 8000
            or raid_plus.get("source", {}).get("scored_rows") != 7627):
        raise ValueError("RAID+ current-model audit has an invalid contract")
    raid_labels = {
        "deepseek-v3": "DeepSeek V3",
        "gemini-3.1-pro": "Gemini 3.1 Pro",
        "gemma-3-27b": "Gemma 3 27B",
        "llama-3.3-70b": "Llama 3.3 70B",
    }
    raid_plus_surface = [
        (raid_labels[model], raid_plus["models"][model]["mean_writing_score"])
        for model in raid_labels
    ]
    quality = json.loads(QUALITY_RESULTS.read_text())
    if (quality.get("result_kind") != "blind_slop_quality_evaluation"
            or quality.get("calibrated_field_accuracy") is not False
            or quality.get("source", {}).get("items") != 72):
        raise ValueError("blind quality evaluation has an invalid contract")
    quality_order = ["original", "de-slop", "stop-slop", "no-ai-slop",
                     "humanizer", "zero-slop"]
    blind_quality = [
        (("Original drafts" if method == "original" else
          "Zero Slop" if method == "zero-slop" else method),
         quality["methods"][method]["mean_blind_severity"])
        for method in quality_order
    ]
    ablation = json.loads(FEATURE_ABLATION.read_text())
    research = ablation.get("structured_contextual_research", {})
    if (ablation.get("schema") != 1 or research.get("field_accuracy") is not False):
        raise ValueError("feature ablation has an invalid contract")
    contextual_ablation = [
        (f"v{ablation['candidate']['version']} local score", round(
            research["surface_accuracy_on_same_items"] * 100, 2)),
        ("contextual research review", round(
            research["held_out_test_accuracy"] * 100, 2)),
    ]
    return {"raid_plus_surface": raid_plus_surface,
            "detector_panel": panel,
            "search_corpus": search_panel,
            "search_rewrite_scores": rewrite_scores,
            "search_rewrite_passes": rewrite_passes,
            "external_checker_clean": external_clean,
            "external_model_context": model_context,
            "beemo_surface": beemo_surface,
            "blind_quality": blind_quality,
            "contextual_ablation": contextual_ablation,
            "incumbent_hidden_preferences": incumbent_hidden_preferences,
            "capability_matrix": capability_matrix}


# ---- rendering (Pillow) --------------------------------------------------
FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
PAPER = (248, 249, 246)
INK, MUTE, GRID = (25, 29, 27), (91, 100, 95), (217, 222, 216)
BRAND, MUTEDBAR = (34, 123, 91), (171, 183, 176)


def _font(size, bold=False):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=1 if bold and path.endswith(".ttc") else 0)
            except Exception:
                continue
    return ImageFont.load_default()


def _hbar(path, title, subtitle, rows, ours_label, axis_ticks=None):
    from PIL import Image, ImageDraw
    W, padL, padR, top, rowh = 1240, 340, 90, 96, 52
    H = top + len(rows) * rowh + 70
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((44, 30), title, font=_font(27, True), fill=INK)
    d.text((44, 66), subtitle, font=_font(15), fill=MUTE)
    vmax = max(axis_ticks) if axis_ticks else (max(v for _, v in rows) * 1.16) or 1
    x0, x1 = padL, W - padR
    ticks = axis_ticks or [vmax * i / 4 for i in range(5)]
    for tick in ticks:
        gx = x0 + (x1 - x0) * tick / vmax
        d.line([(gx, top - 6), (gx, H - 46)], fill=GRID, width=1)
        d.text((gx - 8, H - 40), f"{tick:g}", font=_font(12), fill=MUTE)
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
    # Widened from 1500 when the audit went from five products to seven: at the
    # old width the owner/name labels ran into each other. Long labels also wrap
    # at the slash now, so "JCarterJohnson/unslop-text" stacks instead of
    # overlapping its neighbour.
    W, left, top, rowh = 1760, 620, 172, 43
    products = audit["products"]
    rows = audit["rows"]
    column_left, column_right = 760, W - 90
    centers = [
        column_left + i * (column_right - column_left) / (len(products) - 1)
        for i in range(len(products))
    ]
    H = top + len(rows) * rowh + 112
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((44, 28), "Documented editorial system capabilities",
           font=_font(27, True), fill=INK)
    d.text((44, 66), "Repository audit at pinned commits. Documented does not mean effective.",
           font=_font(15), fill=MUTE)
    d.text((44, 96), "Native = dedicated component or named gate. Guided = instruction or self-check.",
           font=_font(13), fill=MUTE)

    for x, (_, label, commit) in zip(centers, products):
        is_subject = label == "Zero Slop"
        parts = label.split("/", 1)
        lines = [parts[0] + "/", parts[1]] if len(parts) == 2 else [label]
        for line_index, line in enumerate(lines):
            d.text((x, 120 + line_index * 17), line,
                   font=_font(13, is_subject),
                   fill=INK if is_subject else MUTE, anchor="ma")
        d.text((x, 120 + len(lines) * 17 + 3), commit[:8],
               font=_font(10), fill=MUTE, anchor="ma")

    for i, row in enumerate(rows):
        y = top + i * rowh
        if i % 2 == 0:
            d.rounded_rectangle([32, y, W - 32, y + rowh - 2], 5,
                                fill=(241, 244, 240))
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
        ASSETS / "bench-raid-plus.png",
        "Current-model writing scores on RAID+",
        "7,627 non-empty abstracts from four recent models. Lower means less tracked "
        "generic AI-style language; this is not quality or authorship accuracy.",
        datasets["raid_plus_surface"], "__no_highlight__", axis_ticks=[0, 10, 20, 30, 40]))
    out.append(_hbar(
        ASSETS / "bench-detector.png",
        "Generic AI-style language remaining after editing",
        "Detector score, lower means more of the AI accent removed. Scored by Zero Slop's own "
        "meter, so read it as patterns removed, not an independent verdict.",
        datasets["detector_panel"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-search-corpus.png",
        "Search-informed slop challenge",
        "18 anonymous paraphrases, three per genre. Higher means more tracked surface slop; "
        "this is a regression check, not field accuracy.",
        datasets["search_corpus"], None))
    out.append(_hbar(
        ASSETS / "bench-search-rewrites.png",
        "Writing score after a fresh editing replay",
        "Same 18 drafts, model, reasoning level, and batch size. Lower is cleaner on "
        "Zero Slop's meter; this is not an independent verdict.",
        datasets["search_rewrite_scores"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-search-passrate.png",
        "Zero Slop release checks passed",
        "Writing, layout, and protected-detail checks. These are Zero Slop's gates, not field accuracy.",
        datasets["search_rewrite_passes"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-external-checker.png",
        "Reads-clean rate on the public AIStoryHub checker",
        "Corpus v1.8; item-level browser checks; eligible items only (20-word minimum). "
        "Higher is better; 0-1 abstention per method in this replay.",
        datasets["external_checker_clean"], "Zero Slop"))
    out.append(_hbar(
        ASSETS / "bench-beemo.png",
        "External paired-edit writing audit",
        "2,187 Beemo records. Lower means less generic AI-style language; provenance and edit "
        "history are not slop-quality labels.",
        datasets["beemo_surface"], "__no_highlight__"))
    out.append(_hbar(
        ASSETS / "external-model-context.png",
        "External model context: mechanical Slop Index",
        "19,928 preserved generations from 18 models. Lower is closer to a pre-AI "
        "human baseline; the published weights are sensitivity-dependent.",
        datasets["external_model_context"], "__no_highlight__"))
    out.append(_hbar(
        ASSETS / "bench-blind-quality.png",
        "Method-hidden editorial severity after rewriting",
        "Two method-hidden LLM editors; 12 variants per method. Lower is better. "
        "Small clustered panel, with unresolved labels retained; not field accuracy.",
        datasets["blind_quality"], "Zero Slop", axis_ticks=[0, 1, 2, 3, 4, 5]))
    out.append(_hbar(
        ASSETS / "bench-contextual-ablation.png",
        "Held-out contextual research comparison",
        "Cross-rater accuracy on the same eligible method-hidden test items. Higher is better. "
        "LLM editorial reproducibility, not independent human field accuracy.",
        datasets["contextual_ablation"], "contextual research review",
        axis_ticks=[0, 25, 50, 75, 100]))
    out.append(_hbar(
        ASSETS / "bench-incumbent-hidden.png",
        "Method-hidden editorial preference",
        "Consensus across two GPT-5.4 review passes on 18 drafts. Unresolved "
        "means the passes disagreed; not human field accuracy.",
        datasets["incumbent_hidden_preferences"],
        datasets["incumbent_hidden_preferences"][0][0],
        axis_ticks=[0, 3, 6, 9, 12, 15, 18]))
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
