#!/usr/bin/env python3
"""Compare two fixed local meters on the consensus editorial panel."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
QUALITY = ROOT / "bench" / "quality-corpus"
OUTPUT = HERE / "results.json"
sys.path.insert(0, str(ROOT / "scripts"))
from safeio import atomic_write_text  # noqa: E402


def safe_div(a, b):
    return a / b if b else None


def auc(rows):
    positive = [score for label, score in rows if label == "sloppy"]
    negative = [score for label, score in rows if label == "clean"]
    if not positive or not negative:
        return None
    wins = sum(1 if p > n else 0.5 if p == n else 0
               for p in positive for n in negative)
    return wins / (len(positive) * len(negative))


def metrics(rows, gate):
    tp = sum(label == "sloppy" and score >= gate for label, score in rows)
    tn = sum(label == "clean" and score < gate for label, score in rows)
    fp = sum(label == "clean" and score >= gate for label, score in rows)
    fn = sum(label == "sloppy" and score < gate for label, score in rows)
    recall, specificity = safe_div(tp, tp + fn), safe_div(tn, tn + fp)
    precision = safe_div(tp, tp + fp)
    f1 = (None if precision is None or recall is None or precision + recall == 0
          else 2 * precision * recall / (precision + recall))
    return {
        "items": len(rows), "gate": gate,
        "true_positive": tp, "true_negative": tn,
        "false_positive": fp, "false_negative": fn,
        "accuracy": round((tp + tn) / len(rows), 4),
        "balanced_accuracy": round((recall + specificity) / 2, 4),
        "precision": None if precision is None else round(precision, 4),
        "recall": round(recall, 4), "specificity": round(specificity, 4),
        "f1": None if f1 is None else round(f1, 4),
        "roc_auc": round(auc(rows), 4),
    }


def incumbent_scores(root, items):
    script = r"""
const fs = require('node:fs');
const path = require('node:path');
const detector = require(path.join(process.argv[1], 'detector', 'patterns.js'));
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(rows.map((row) => {
  const result = detector.analyzeText(row.text);
  return {id: row.id, score: result.score,
    issue_types: [...new Set(result.issues.map((issue) => issue.type))]};
})));
"""
    completed = subprocess.run(
        ["node", "-e", script, str(root.resolve())], input=json.dumps(items),
        text=True, capture_output=True, check=True,
    )
    return {row["id"]: row for row in json.loads(completed.stdout)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--avoid-root", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    patterns = args.avoid_root / "detector" / "patterns.js"
    if not patterns.is_file():
        parser.error("--avoid-root must be a pinned avoid-ai-writing checkout")

    manifest = json.loads((QUALITY / "manifest.json").read_text())
    label_sets = [json.loads((QUALITY / name).read_text())["items"] for name in
                  ("labels-rater-a.json", "labels-rater-b.json")]
    labels = [{row["id"]: row["label"] for row in rows} for rows in label_sets]
    eligible = []
    for item in manifest["items"]:
        votes = {label[item["id"]] for label in labels}
        if len(votes) == 1 and next(iter(votes)) in {"clean", "sloppy"}:
            eligible.append({**item, "consensus": next(iter(votes))})

    measured = incumbent_scores(args.avoid_root, eligible)
    rows = [(item["consensus"], measured[item["id"]]["score"])
            for item in eligible]
    dev = [(item["consensus"], measured[item["id"]]["score"])
           for item in eligible if item["split"] == "dev"]
    test = [(item["consensus"], measured[item["id"]]["score"])
            for item in eligible if item["split"] == "test"]
    candidates = [metrics(dev, gate) for gate in range(1, 101)]
    chosen = max(candidates, key=lambda row: (
        row["balanced_accuracy"], row["accuracy"], -abs(row["gate"] - 16)
    ))["gate"]
    issue_types = ("punct-distribution", "fnword-trigram-entropy",
                   "cross-para-burstiness", "low-ttr", "uniformity")
    result = {
        "schema": 1,
        "result_kind": "pinned_incumbent_meter_transfer_audit",
        "calibrated_field_accuracy": False,
        "incumbent": {
            "repository": "https://github.com/conorbronsdon/avoid-ai-writing",
            "commit": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=args.avoid_root,
                capture_output=True, text=True, check=True,
            ).stdout.strip(),
            "published_gate": 16,
            "published_gate_metrics": {
                "all": metrics(rows, 16), "dev": metrics(dev, 16),
                "test": metrics(test, 16),
            },
            "dev_selected_gate": chosen,
            "held_out_at_dev_selected_gate": metrics(test, chosen),
            "candidate_signal_firings": {
                name: sum(name in measured[item["id"]]["issue_types"]
                          for item in eligible)
                for name in issue_types
            },
        },
        "zero_slop_current_fixed_gate": json.loads(
            (QUALITY / "results.json").read_text()
        )["surface_meter"],
        "panel": {
            "eligible_consensus_items": len(eligible),
            "dev_items": len(dev), "held_out_test_items": len(test),
            "labels": "Consensus clean/sloppy calls from two method-hidden LLM editorial raters; disagreements and borderline calls abstain.",
        },
        "limits": (
            "This small clustered LLM-labelled panel measures transfer to an editorial "
            "rubric, not human field accuracy or authorship. The dev-selected incumbent "
            "gate is reported only on held-out test items; the incumbent's published gate "
            "is also shown without retuning."
        ),
    }
    rendered = json.dumps(result, indent=1) + "\n"
    if args.write:
        atomic_write_text(OUTPUT, rendered)
        print(f"wrote {OUTPUT}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
