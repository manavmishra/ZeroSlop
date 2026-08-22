#!/usr/bin/env python3
"""Score the anonymous, search-informed cross-genre slop challenge corpus.

The corpus contains paraphrases, not copied public posts. It is intentionally
made of obvious positive examples, so the result is a regression check for easy
slop rather than an accuracy estimate for writing in the wild.
"""
import argparse
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402

CORPUS = HERE / "corpus.json"
RESULTS = HERE / "results.json"
GATE = 25.0


def compute():
    data = slopscore.load_patterns()
    rows = json.loads(CORPUS.read_text())
    scored = []
    for row in rows:
        formal = row["genre"] == "research"
        result = slopscore.score_text(row["text"], data, formal=formal)
        shape_genre = "social" if row["genre"] in {"linkedin", "x"} else "general"
        shape = slopscore.shape_metrics(row["text"], genre=shape_genre)
        scored.append({
            "id": row["id"],
            "genre": row["genre"],
            "surface_score": result["ai_likelihood"],
            "weighted_tells": len(result["hits"]),
            "burstiness": result["burstiness"],
            "broetry": shape.get("broetry"),
            "caught": result["ai_likelihood"] > GATE or bool(shape.get("broetry")),
        })

    by_genre = {}
    for genre in sorted({row["genre"] for row in scored}):
        values = [row["surface_score"] for row in scored if row["genre"] == genre]
        by_genre[genre] = {
            "n": len(values),
            "mean_surface_score": round(st.mean(values), 1),
            "range": [min(values), max(values)],
            "caught": sum(row["caught"] for row in scored if row["genre"] == genre),
        }
    return {
        "corpus": "anonymous-search-paraphrases-v1",
        "gate": GATE,
        "n_examples": len(scored),
        "caught": sum(row["caught"] for row in scored),
        "by_genre": by_genre,
        "rows": scored,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="refresh results.json")
    parser.add_argument("--check", action="store_true", help="fail if results.json is stale")
    args = parser.parse_args()
    fresh = compute()
    if args.write:
        RESULTS.write_text(json.dumps(fresh, indent=1) + "\n")
    if args.check:
        if not RESULTS.exists() or json.loads(RESULTS.read_text()) != fresh:
            print("search-corpus results are stale; run evaluate.py --write")
            return 1
    print(f"caught {fresh['caught']}/{fresh['n_examples']} obvious-slop paraphrases")
    for genre, row in fresh["by_genre"].items():
        print(f"  {genre:10s} {row['caught']}/{row['n']}  mean {row['mean_surface_score']:5.1f}  "
              f"range {row['range'][0]:.1f}-{row['range'][1]:.1f}")
    return 0 if fresh["caught"] == fresh["n_examples"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
