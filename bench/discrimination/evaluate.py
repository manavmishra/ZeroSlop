#!/usr/bin/env python3
"""Test whether the surface and social-shape gates separate labeled examples."""
import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402

GATE = 25.0
LABELS = {"slop", "human"}


def load_rows(path):
    try:
        rows = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read a valid discrimination corpus: {exc}") from exc
    if not isinstance(rows, list) or not rows:
        raise ValueError("discrimination corpus must be a non-empty list")
    seen = set()
    for index, row in enumerate(rows):
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or not row["id"].strip() or row["id"] in seen
                or not isinstance(row.get("genre"), str) or not row["genre"].strip()
                or row.get("label") not in LABELS
                or not isinstance(row.get("text"), str) or not row["text"].strip()):
            raise ValueError(f"invalid or duplicate corpus row at index {index}")
        seen.add(row["id"])
    if {row["label"] for row in rows} != LABELS:
        raise ValueError("discrimination corpus needs both slop and human labels")
    return rows


def compute(rows):
    data = slopscore.load_patterns()
    scored = []
    for row in rows:
        formal = row["genre"] in {"research", "professional"}
        surface = slopscore.score_text(row["text"], data, formal=formal)
        shape_genre = "social" if row["genre"] in {
            "linkedin", "social", "reddit", "x"
        } else "general"
        shape = slopscore.shape_metrics(row["text"], genre=shape_genre)
        shape_fail = bool(shape.get("broetry"))
        scored.append({
            "id": row["id"], "genre": row["genre"], "label": row["label"],
            "score": surface["ai_likelihood"], "tells": len(surface["hits"]),
            "shape_fail": shape_fail,
            "pred": "slop" if surface["ai_likelihood"] > GATE or shape_fail else "human",
        })
    return scored


def main():
    try:
        rows = compute(load_rows(HERE / "corpus.json"))
        slop = [row["score"] for row in rows if row["label"] == "slop"]
        human = [row["score"] for row in rows if row["label"] == "human"]
        print(f"{'id':22s} {'genre':10s} {'label':6s} {'score':>7s} {'tells':>6s}  verdict")
        for row in sorted(rows, key=lambda item: -item["score"]):
            verdict = "ok" if row["pred"] == row["label"] else "MISCLASSIFIED"
            shape = " +shape" if row["shape_fail"] else ""
            print(f"{row['id']:22s} {row['genre']:10s} {row['label']:6s} "
                  f"{row['score']:7.1f} {row['tells']:6d}  {verdict}{shape}")
        correct = sum(row["pred"] == row["label"] for row in rows)
        pairs = [(a > b) + 0.5 * (a == b) for a in slop for b in human]
        auc = sum(pairs) / len(pairs)
        if not math.isfinite(auc):
            raise ValueError("AUC is not finite")
        print(f"\n  slop   n={len(slop):2d}  mean {st.mean(slop):5.1f}  "
              f"range {min(slop):.1f}-{max(slop):.1f}")
        print(f"  human  n={len(human):2d}  mean {st.mean(human):5.1f}  "
              f"range {min(human):.1f}-{max(human):.1f}")
        print(f"  separation: {st.mean(slop) - st.mean(human):.1f} points")
        print(f"  AUC: {auc:.3f}   accuracy at gate {GATE:g} plus shape: "
              f"{correct}/{len(rows)}")
        overlap = max(human) >= min(slop)
        detail = (f"YES — worst human {max(human):.1f} >= best slop {min(slop):.1f}"
                  if overlap else "no, cleanly separated")
        print(f"  surface classes overlap: {detail}")
        return 0 if correct == len(rows) else 1
    except ValueError as exc:
        print(f"discrimination benchmark: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
