#!/usr/bin/env python3
"""Compare anti-slop instruction sets on the same anonymous corpus.

One host model produced every rewrite from pinned instructions. The surface
meter belongs to Zero Slop, so this is a reproducible register-removal panel,
not an independent ranking or a field-accuracy estimate.
"""
import argparse
import hashlib
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUTS = HERE / "outputs"
RESULTS = HERE / "comparison-results.json"
CHECKER_RESULTS = HERE / "aistoryhub-checker-results.json"
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402
from safeio import atomic_write_text  # noqa: E402


def gate_for(genre):
    return slopscore.RW_GATE.get(genre, slopscore.RW_GATE_DEFAULT)


def evaluate_text(text, genre, data):
    formal = genre in slopscore.RW_FORMAL
    scored = slopscore.score_text(text, data, formal=formal)
    shape_genre = "social" if genre in {"linkedin", "x"} else "general"
    shape = slopscore.shape_metrics(text, genre=shape_genre)
    surface_pass = scored["ai_likelihood"] <= gate_for(genre)
    shape_pass = not bool(shape.get("broetry"))
    return scored, surface_pass, shape_pass


def canonical_hash(rows):
    raw = json.dumps(
        rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def external_checker_summary(source_sets, labels, expected_ids):
    observed = json.loads(CHECKER_RESULTS.read_text())
    if (not isinstance(observed, dict)
            or observed.get("result_kind") != "public_checker_observation"
            or not isinstance(observed.get("inputs"), dict)):
        raise ValueError("aistoryhub-checker-results.json has an invalid contract")
    minimum = observed.get("minimum_words")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise ValueError("external checker minimum_words must be positive")
    clean_below = observed.get("reads_clean_below")
    if (not isinstance(clean_below, int) or isinstance(clean_below, bool)
            or not 1 <= clean_below <= 100):
        raise ValueError("external checker reads_clean_below must be valid")
    if set(observed["inputs"]) != set(source_sets):
        raise ValueError("external checker methods do not match the rewrite panel")

    methods = {}
    for method, texts in source_sets.items():
        record = observed["inputs"][method]
        if not isinstance(record, dict) or not isinstance(record.get("rows"), dict):
            raise ValueError(f"external checker record {method!r} is invalid")
        if record.get("input_sha256") != canonical_hash(texts):
            raise ValueError(
                f"external checker inputs changed for {method}; rerun the public checker"
            )
        rows = record["rows"]
        if set(rows) != expected_ids:
            raise ValueError(f"external checker ids do not match for {method}")
        values, abstentions = [], 0
        for item_id, value in rows.items():
            eligible = len(texts[item_id].split()) >= minimum
            if value is None:
                if eligible:
                    raise ValueError(
                        f"external checker unexpectedly abstained on {method}:{item_id}"
                    )
                abstentions += 1
                continue
            if (not isinstance(value, int) or isinstance(value, bool)
                    or not 0 <= value <= 100):
                raise ValueError(f"external checker score is invalid for {method}:{item_id}")
            if not eligible:
                raise ValueError(
                    f"external checker scored an ineligible item {method}:{item_id}"
                )
            values.append(value)
        if not values:
            raise ValueError(f"external checker has no eligible scores for {method}")
        methods[method] = {
            "label": labels[method],
            "eligible_items": len(values),
            "abstentions": abstentions,
            "mean_score": round(st.mean(values), 1),
            "reads_clean": sum(value < clean_below for value in values),
            "reads_clean_rate": round(
                100 * sum(value < clean_below for value in values) / len(values), 1
            ),
            "mostly_clean_or_better": sum(value < 35 for value in values),
            "mostly_clean_or_better_rate": round(
                100 * sum(value < 35 for value in values) / len(values), 1
            ),
        }
    return {
        "result_kind": observed["result_kind"],
        "checker_url": observed["checker_url"],
        "corpus_url": observed["corpus_url"],
        "corpus_version": observed["corpus_version"],
        "observed": observed["observed"],
        "minimum_words": minimum,
        "reads_clean_below": clean_below,
        "limits": (
            "Deterministic public corpus checker; surface checklist only. "
            "Not rewrite quality, semantic fidelity, field accuracy, or authorship."
        ),
        "methods": methods,
    }


def compute():
    corpus = json.loads((HERE / "corpus.json").read_text())
    metadata = json.loads((HERE / "methods.json").read_text())
    if not isinstance(corpus, list) or not corpus:
        raise ValueError("corpus.json must be a non-empty list")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("methods"), dict):
        raise ValueError("methods.json must contain a methods object")
    ids = [row.get("id") for row in corpus if isinstance(row, dict)]
    if len(ids) != len(corpus) or any(not isinstance(item_id, str) for item_id in ids):
        raise ValueError("every corpus row needs a string id")
    if len(ids) != len(set(ids)):
        raise ValueError("corpus ids must be unique")
    for row in corpus:
        if (not isinstance(row.get("text"), str) or not row["text"].strip()
                or not isinstance(row.get("genre"), str)):
            raise ValueError(f"{row.get('id')!r}: text must be non-empty and genre must be a string")
    expected = {row["id"] for row in corpus}
    data = slopscore.load_patterns()

    source_sets = {"original": {row["id"]: row["text"] for row in corpus}}
    labels = {"original": "Original drafts"}
    original_evaluations = [evaluate_text(row["text"], row["genre"], data)
                            for row in corpus]
    original_scores = [result[0]["ai_likelihood"] for result in original_evaluations]
    original_passes = sum(surface and shape
                          for _, surface, shape in original_evaluations)
    methods = {}
    for method, method_meta in metadata["methods"].items():
        path = OUTPUTS / f"{method}.json"
        rewrites = json.loads(path.read_text())
        if not isinstance(rewrites, dict):
            raise ValueError(f"{path.name}: expected an object keyed by corpus id")
        if set(rewrites) != expected:
            missing = sorted(expected - set(rewrites))
            extra = sorted(set(rewrites) - expected)
            raise ValueError(f"{path.name}: missing={missing}, extra={extra}")
        source_sets[method] = rewrites
        labels[method] = method_meta["label"]

        rows = []
        for source in corpus:
            rewritten = rewrites[source["id"]]
            if not isinstance(rewritten, str) or not rewritten.strip():
                raise ValueError(f"{path.name}:{source['id']}: rewrite must be non-empty text")
            scored, surface_pass, shape_pass = evaluate_text(
                rewritten, source["genre"], data)
            fidelity = slopscore.fidelity(source["text"], rewritten)
            fact_pass = fidelity["preserved"] and not fidelity["invented"]
            editorial_pass = surface_pass and shape_pass
            rows.append({
                "id": source["id"],
                "genre": source["genre"],
                "surface_score": scored["ai_likelihood"],
                "gate": gate_for(source["genre"]),
                "surface_gate_pass": surface_pass,
                "shape_gate_pass": shape_pass,
                "editorial_gate_pass": editorial_pass,
                "automated_fact_check_pass": fact_pass,
                "combined_pass": editorial_pass and fact_pass,
                "words_before": len(source["text"].split()),
                "words_after": len(rewritten.split()),
            })

        by_genre = {}
        for genre in sorted({row["genre"] for row in rows}):
            selected = [row for row in rows if row["genre"] == genre]
            by_genre[genre] = {
                "n": len(selected),
                "mean_surface_score": round(st.mean(
                    row["surface_score"] for row in selected), 1),
                "combined_passes": sum(row["combined_pass"] for row in selected),
            }
        methods[method] = {
            "label": method_meta["label"],
            "mean_surface_score": round(st.mean(
                row["surface_score"] for row in rows), 1),
            "mean_score_reduction": round(st.mean(original_scores) - st.mean(
                row["surface_score"] for row in rows), 1),
            "surface_gate_passes": sum(row["surface_gate_pass"] for row in rows),
            "shape_gate_passes": sum(row["shape_gate_pass"] for row in rows),
            "editorial_gate_passes": sum(row["editorial_gate_pass"] for row in rows),
            "automated_fact_check_passes": sum(
                row["automated_fact_check_pass"] for row in rows),
            "combined_passes": sum(row["combined_pass"] for row in rows),
            "combined_pass_rate": round(100 * sum(
                row["combined_pass"] for row in rows) / len(rows), 1),
            "mean_word_change_pct": round(st.mean(
                100 * (row["words_after"] - row["words_before"])
                / row["words_before"] for row in rows), 1),
            "by_genre": by_genre,
            "rows": rows,
        }

    external = external_checker_summary(source_sets, labels, expected)
    return {
        "corpus": "anonymous-search-paraphrases-v1",
        "n_examples": len(corpus),
        "generation": {
            "run_id": metadata["run_id"],
            "generated_at": metadata["generated_at"],
            "generator": metadata["generator"],
            "model_record": metadata["model_record"],
            "prompt": metadata["prompt"],
            "method_revisions": {
                key: {k: v for k, v in value.items() if k != "label"}
                for key, value in metadata["methods"].items()
            },
        },
        "metric_limits": {
            "surface": "Zero Slop's heuristic meter; lower is cleaner",
            "combined_pass": "genre surface and shape gates plus automated names, figures, quotes, links, and asserted-feelings check",
            "not_measured": "semantic fidelity, human preference, field accuracy, authorship",
        },
        "original_mean_surface_score": round(st.mean(original_scores), 1),
        "original_combined_passes": original_passes,
        "original_combined_pass_rate": round(100 * original_passes / len(corpus), 1),
        "external_cross_meter": external,
        "methods": methods,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    fresh = compute()
    if args.write:
        atomic_write_text(RESULTS, json.dumps(fresh, indent=1) + "\n")
    if args.check and (not RESULTS.exists() or
                       json.loads(RESULTS.read_text()) != fresh):
        print("comparison results are stale; run compare.py --write")
        return 1
    print(f"anti-slop comparison on {fresh['n_examples']} items")
    print(f"  {'method':14s} {'score':>7s} {'gate+fact':>11s} {'word delta':>11s}")
    for row in fresh["methods"].values():
        print(f"  {row['label']:14s} {row['mean_surface_score']:7.1f} "
              f"{row['combined_passes']:>2}/{fresh['n_examples']:<2} "
              f"{row['mean_word_change_pct']:>+10.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
