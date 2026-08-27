#!/usr/bin/env python3
"""Map method-hidden judgments, add deterministic gates, and publish results."""
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
OUTPUT = HERE / "results.json"
METHODS = ("zero-slop", "avoid-ai-writing")
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def incumbent_batch(root, corpus, outputs):
    script = r"""
const fs = require('node:fs');
const path = require('node:path');
const root = process.argv[1];
const detector = require(path.join(root, 'detector', 'patterns.js'));
const validator = require(path.join(root, 'detector', 'validate.js'));
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(rows.map((row) => {
  const scored = detector.analyzeText(row.after, {contextMode: row.context});
  const kept = validator.validate(row.before, row.after, {skipResidual: true});
  return {key: row.key, score: scored.score, preservation: kept.ok,
    unscored: Boolean(scored.tooShort || scored.tooLong)};
})));
"""
    rows = []
    for method in METHODS:
        for item in corpus:
            context = "technical" if item["genre"] == "research" else (
                "marketing" if item["genre"] in {"email", "linkedin"} else "general"
            )
            rows.append({"key": f"{method}::{item['id']}", "before": item["text"],
                         "after": outputs[method][item["id"]], "context": context})
    completed = subprocess.run(["node", "-e", script, str(root.resolve())],
                               input=json.dumps(rows), text=True,
                               capture_output=True, check=True)
    return {row["key"]: row for row in json.loads(completed.stdout)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--avoid-root", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    corpus = json.loads(CORPUS.read_text())
    outputs = {m: json.loads((HERE / "outputs" / f"{m}.json").read_text())
               for m in METHODS}
    runs = {m: json.loads((HERE / "runs" / f"{m}.json").read_text()) for m in METHODS}
    expected = [row["id"] for row in corpus]
    for method in METHODS:
        if list(outputs[method]) != expected:
            raise SystemExit(f"{method}: output IDs drifted")
        if runs[method]["output_sha256"] != sha(HERE / "outputs" / f"{method}.json"):
            raise SystemExit(f"{method}: output hash drifted")
    for field in ("model", "reasoning_effort", "batch_size", "codex_cli", "corpus_sha256"):
        if len({runs[m][field] for m in METHODS}) != 1:
            raise SystemExit(f"generation mismatch on {field}")

    review_run = json.loads((HERE / "review-run.json").read_text())
    pass_rows = []
    mapped_by_pass = []
    dimensions = ("source_preservation", "naturalness", "clarity", "mechanics")
    dimension_values = {m: {d: [] for d in dimensions} for m in METHODS}
    for record in review_run["passes"]:
        n = record["pass"]
        packet_path = HERE / "packets" / f"pass-{n}.json"
        map_path = HERE / "maps" / f"pass-{n}.json"
        judgment_path = HERE / "judgments" / f"pass-{n}.json"
        if (record["packet_sha256"] != sha(packet_path)
                or record["mapping_sha256"] != sha(map_path)
                or record["judgment_sha256"] != sha(judgment_path)):
            raise SystemExit(f"review pass {n} hash drifted")
        mapping = json.loads(map_path.read_text())
        judgments = json.loads(judgment_path.read_text())["judgments"]
        if [row["id"] for row in judgments] != expected:
            raise SystemExit(f"review pass {n} IDs drifted")
        counts = {"zero-slop": 0, "avoid-ai-writing": 0, "tie": 0}
        mapped = {}
        for row in judgments:
            winner = "tie" if row["winner"] == "tie" else mapping[row["id"]][row["winner"]]
            counts[winner] += 1
            mapped[row["id"]] = {"winner": winner, "reason": row["reason"]}
            for letter, score_key in (("A", "a"), ("B", "b")):
                method = mapping[row["id"]][letter]
                for dimension in dimensions:
                    dimension_values[method][dimension].append(row[score_key][dimension])
        pass_rows.append({"pass": n, "positions_seed": record["seed"], "preferences": counts})
        mapped_by_pass.append(mapped)

    consensus = {"zero-slop": 0, "avoid-ai-writing": 0, "tie": 0, "unresolved": 0}
    exact_agreement = 0
    items = []
    for item_id in expected:
        first, second = mapped_by_pass[0][item_id], mapped_by_pass[1][item_id]
        if first["winner"] == second["winner"]:
            exact_agreement += 1
            consensus[first["winner"]] += 1
            outcome = first["winner"]
        else:
            consensus["unresolved"] += 1
            outcome = "unresolved"
        items.append({"id": item_id, "consensus": outcome,
                      "pass_1": first, "pass_2": second})

    data = slopscore.load_patterns()
    incumbent = incumbent_batch(args.avoid_root, corpus, outputs)
    deterministic = {}
    for method in METHODS:
        rows = []
        for item in corpus:
            text = outputs[method][item["id"]]
            measured = slopscore.score_text(text, data, formal=item["genre"] == "research")
            shape_genre = "social" if item["genre"] in {"linkedin", "x"} else "general"
            gate = slopscore.RW_GATE.get(item["genre"], slopscore.RW_GATE_DEFAULT)
            fidelity = slopscore.fidelity(item["text"], text)
            inc = incumbent[f"{method}::{item['id']}"]
            rows.append({
                "id": item["id"], "writing_score": round(measured["ai_likelihood"], 1),
                "zero_slop_release_pass": measured["ai_likelihood"] <= gate
                    and not slopscore.shape_metrics(text, genre=shape_genre).get("broetry")
                    and fidelity["preserved"] and not fidelity["invented"],
                "zero_slop_fidelity_pass": fidelity["preserved"] and not fidelity["invented"],
                "incumbent_score": inc["score"],
                "incumbent_preservation_pass": inc["preservation"],
                "incumbent_unscored": inc["unscored"],
            })
        deterministic[method] = {
            "mean_writing_score": round(st.mean(row["writing_score"] for row in rows), 1),
            "zero_slop_release_passes": sum(row["zero_slop_release_pass"] for row in rows),
            "zero_slop_fidelity_passes": sum(row["zero_slop_fidelity_pass"] for row in rows),
            "mean_incumbent_score": round(st.mean(row["incumbent_score"] for row in rows), 1),
            "incumbent_preservation_passes": sum(row["incumbent_preservation_pass"] for row in rows),
            "incumbent_unscored": sum(row["incumbent_unscored"] for row in rows),
            "rows": rows,
        }

    result = {
        "schema": 1, "result_kind": "fresh_method_hidden_incumbent_rewrite_comparison",
        "calibrated_field_accuracy": False,
        "corpus": {"drafts": len(corpus), "genres": len({r['genre'] for r in corpus}),
                   "sha256": sha(CORPUS),
                   "selection": "Deliberately obvious, search-informed regression drafts; not a representative field sample."},
        "generation": {field: runs["zero-slop"][field] for field in
                       ("model", "reasoning_effort", "batch_size", "codex_cli")},
        "methods": {m: {"label": runs[m]["label"], "revision": runs[m]["revision"]}
                    for m in METHODS},
        "editorial_review": {
            "method_hidden": True, "passes": pass_rows,
            "exact_winner_agreement": {"items": exact_agreement,
                                       "rate": round(exact_agreement / len(corpus), 4)},
            "consensus": consensus,
            "mean_dimension_scores": {
                m: {d: round(st.mean(dimension_values[m][d]), 2) for d in dimensions}
                for m in METHODS
            },
            "items": items,
        },
        "deterministic_checks": deterministic,
        "limits": "Both methods used the same model, settings, corpus, and batch size. Method names were absent from review packets and A/B positions were reshuffled independently. The reviewer was an LLM, hosted seeds are unavailable, and the corpus is small and deliberately obvious; this is not independent human field accuracy or a universal ranking.",
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=1) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
        print(f"wrote {OUTPUT}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
