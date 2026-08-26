#!/usr/bin/env python3
"""Evaluate pinned fresh-replay outputs with two meters and two fidelity gates."""
import argparse
import hashlib
import json
import statistics as st
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPUS = ROOT / "bench" / "search-corpus" / "corpus.json"
RESULTS = HERE / "results.json"
METHODS = ("zero-slop", "avoid-ai-writing", "no-ai-slop", "humanizer")
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def avoid_batch(avoid_root, rows):
    """Run the incumbent's meter and preservation validator in one Node process."""
    script = r"""
const fs = require('node:fs');
const path = require('node:path');
const root = process.argv[1];
const detector = require(path.join(root, 'detector', 'patterns.js'));
const validator = require(path.join(root, 'detector', 'validate.js'));
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = rows.map((row) => {
  const measured = detector.analyzeText(row.after, { contextMode: row.context });
  const kept = validator.validate(row.before, row.after, { skipResidual: true });
  return {
    id: row.id,
    score: measured.score,
    classification: measured.document_classification,
    too_short: Boolean(measured.tooShort),
    too_long: Boolean(measured.tooLong),
    preservation_ok: kept.ok,
    preservation_errors: kept.errors.map((item) => item.code),
  };
});
process.stdout.write(JSON.stringify(out));
"""
    completed = subprocess.run(
        ["node", "-e", script, str(avoid_root.resolve())],
        input=json.dumps(rows), text=True, capture_output=True, check=True,
    )
    return {row["id"]: row for row in json.loads(completed.stdout)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--avoid-root", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not (args.avoid_root / "detector" / "patterns.js").is_file():
        parser.error("--avoid-root must be a pinned avoid-ai-writing checkout")

    corpus = json.loads(CORPUS.read_text())
    originals = {row["id"]: row for row in corpus}
    expected_ids = list(originals)
    runs, outputs = {}, {}
    for method in METHODS:
        run_path = HERE / "runs" / f"{method}.json"
        output_path = HERE / "outputs" / f"{method}.json"
        if not run_path.is_file() or not output_path.is_file():
            raise SystemExit(f"missing fresh replay artifact for {method}")
        runs[method] = json.loads(run_path.read_text())
        outputs[method] = json.loads(output_path.read_text())
        if list(outputs[method]) != expected_ids:
            raise SystemExit(f"{method}: output IDs do not match the frozen corpus")
        if runs[method]["output_sha256"] != sha256(output_path):
            raise SystemExit(f"{method}: output hash does not match its run record")

    settings = ("model", "reasoning_effort", "batch_size", "codex_cli",
                "corpus_sha256")
    for field in settings:
        values = {runs[method][field] for method in METHODS}
        if len(values) != 1:
            raise SystemExit(f"fresh replay methods differ on {field}: {values}")

    data = slopscore.load_patterns()
    original_rows = []
    for item in corpus:
        formal = item["genre"] == "research"
        measured = slopscore.score_text(item["text"], data, formal=formal)
        genre = "social" if item["genre"] in {"linkedin", "x"} else "general"
        shape = slopscore.shape_metrics(item["text"], genre=genre)
        gate = slopscore.RW_GATE.get(item["genre"], slopscore.RW_GATE_DEFAULT)
        original_rows.append({
            "id": item["id"],
            "genre": item["genre"],
            "writing_score": round(measured["ai_likelihood"], 1),
            "writing_gate": gate,
            "writing_gate_pass": measured["ai_likelihood"] <= gate,
            "shape_gate_pass": not bool(shape.get("broetry")),
        })
    rows_by_method = {}
    avoid_input = []
    for method in METHODS:
        rows = []
        for item in corpus:
            after = outputs[method][item["id"]]
            formal = item["genre"] == "research"
            measured = slopscore.score_text(after, data, formal=formal)
            genre = "social" if item["genre"] in {"linkedin", "x"} else "general"
            shape = slopscore.shape_metrics(after, genre=genre)
            gate = slopscore.RW_GATE.get(item["genre"], slopscore.RW_GATE_DEFAULT)
            fid = slopscore.fidelity(item["text"], after)
            row = {
                "id": item["id"],
                "genre": item["genre"],
                "writing_score": round(measured["ai_likelihood"], 1),
                "writing_gate": gate,
                "writing_gate_pass": measured["ai_likelihood"] <= gate,
                "shape_gate_pass": not bool(shape.get("broetry")),
                "zero_slop_fidelity_pass": fid["preserved"] and not fid["invented"],
                "word_change_pct": round(
                    (len(after.split()) / max(1, len(item["text"].split())) - 1) * 100,
                    1,
                ),
            }
            rows.append(row)
            context = "technical" if item["genre"] == "research" else (
                "marketing" if item["genre"] in {"email", "linkedin"} else "general"
            )
            avoid_input.append({"method": method, "id": item["id"],
                                "before": item["text"], "after": after,
                                "context": context})
        rows_by_method[method] = rows

    # IDs repeat across methods, so qualify them before the shared Node pass.
    avoid_qualified = avoid_batch(args.avoid_root, [
        {**row, "id": f"{row['method']}::{row['id']}"} for row in avoid_input
    ])
    methods = {}
    for method, rows in rows_by_method.items():
        for row in rows:
            incumbent = avoid_qualified[f"{method}::{row['id']}"]
            row.update({
                "incumbent_score": incumbent["score"],
                "incumbent_preservation_pass": incumbent["preservation_ok"],
                "incumbent_unscored": incumbent["too_short"] or incumbent["too_long"],
            })
            row["zero_slop_release_pass"] = (
                row["writing_gate_pass"] and row["shape_gate_pass"]
                and row["zero_slop_fidelity_pass"]
            )
        methods[method] = {
            "label": runs[method]["label"],
            "revision": runs[method]["revision"],
            "mean_writing_score": round(st.mean(row["writing_score"] for row in rows), 1),
            "median_writing_score": round(st.median(row["writing_score"] for row in rows), 1),
            "zero_slop_release_passes": sum(row["zero_slop_release_pass"] for row in rows),
            "zero_slop_fidelity_passes": sum(row["zero_slop_fidelity_pass"] for row in rows),
            "mean_incumbent_score": round(st.mean(row["incumbent_score"] for row in rows), 1),
            "incumbent_preservation_passes": sum(row["incumbent_preservation_pass"] for row in rows),
            "incumbent_unscored": sum(row["incumbent_unscored"] for row in rows),
            "mean_word_change_pct": round(st.mean(row["word_change_pct"] for row in rows), 1),
            "rows": rows,
        }

    result = {
        "schema": 1,
        "result_kind": "fresh_same_model_rewrite_replay",
        "calibrated_field_accuracy": False,
        "corpus": {
            "path": "bench/search-corpus/corpus.json",
            "sha256": next(iter(runs.values()))["corpus_sha256"],
            "drafts": len(corpus),
            "genres": len({row["genre"] for row in corpus}),
            "selection": "Deliberately obvious, search-informed regression drafts; not a representative field sample.",
        },
        "generation": {field: next(iter(runs.values()))[field] for field in settings[:-1]},
        "originals": {
            "label": "Original drafts",
            "mean_writing_score": round(
                st.mean(row["writing_score"] for row in original_rows), 1
            ),
            "zero_slop_release_passes": sum(
                row["writing_gate_pass"] and row["shape_gate_pass"]
                for row in original_rows
            ),
            "rows": original_rows,
        },
        "methods": methods,
        "limits": (
            "All methods used the same model, reasoning setting, batch size, and corpus. "
            "The writing and release gates belong to Zero Slop; the incumbent score and "
            "preservation gate belong to avoid-ai-writing. This is a reproducible regression "
            "and cross-meter comparison, not independent human field accuracy. Hosted "
            "inference seeds are not exposed."
        ),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=1) + "\n"
    if args.write:
        RESULTS.write_text(rendered)
        print(f"wrote {RESULTS}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
