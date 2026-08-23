#!/usr/bin/env python3
"""Evaluate the surface meter and editing methods on blind quality labels."""
import argparse
import hashlib
import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402
from safeio import atomic_write_text  # noqa: E402
from common import ContractError, load_manifest, read_json  # noqa: E402

LABELS = {"clean", "sloppy", "borderline"}
SIGNALS = {
    "hollow_substance", "semantic_redundancy", "vague_reference",
    "canned_framing", "genre_mismatch", "local_repetition",
    "unsupported_attribution", "reader_process_leak", "rhythm", "formatting",
}
GATE = 25.0


def load_labels(path, manifest):
    data = read_json(path, "labels", limit=5 * 1024 * 1024)
    if (not isinstance(data, dict)
            or set(data) != {"schema", "rater", "protocol_sha256", "items"}
            or data.get("schema") != 1
            or not isinstance(data.get("rater"), str)
            or not data["rater"].strip()
            or data.get("protocol_sha256") != manifest["label_protocol_sha256"]
            or not isinstance(data.get("items"), list)):
        raise ContractError(f"labels {path} have an invalid root contract")
    expected_ids = {item["id"] for item in manifest["items"]}
    rows = {}
    for index, item in enumerate(data["items"], 1):
        if (not isinstance(item, dict)
                or set(item) != {"id", "label", "severity", "signals"}
                or item.get("id") not in expected_ids or item["id"] in rows
                or item.get("label") not in LABELS
                or not isinstance(item.get("severity"), int)
                or isinstance(item.get("severity"), bool)
                or not 1 <= item["severity"] <= 5
                or not isinstance(item.get("signals"), list)
                or len(item["signals"]) != len(set(item["signals"]))
                or any(signal not in SIGNALS for signal in item["signals"])):
            raise ContractError(f"labels {path} item {index} is malformed")
        if ((item["label"] == "clean" and item["severity"] > 2)
                or (item["label"] == "borderline" and item["severity"] != 3)
                or (item["label"] == "sloppy" and item["severity"] < 4)
                or (item["label"] == "clean" and item["signals"])
                or (item["label"] == "sloppy" and not item["signals"])):
            raise ContractError(f"labels {path} item {index} is internally inconsistent")
        rows[item["id"]] = item
    if set(rows) != expected_ids:
        raise ContractError(f"labels {path} do not cover every manifest item")
    return data["rater"], rows


def safe_div(a, b):
    return a / b if b else None


def rounded(value):
    return None if value is None else round(value, 4)


def wilson(k, n, z=1.96):
    if not n:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, center - half), 4), round(min(1, center + half), 4)]


def auc(rows):
    positives = [score for label, score in rows if label == "sloppy"]
    negatives = [score for label, score in rows if label == "clean"]
    if not positives or not negatives:
        return None
    wins = sum(1 if positive > negative else 0.5 if positive == negative else 0
               for positive in positives for negative in negatives)
    return wins / (len(positives) * len(negatives))


def binary_metrics(rows):
    tp = sum(label == "sloppy" and score >= GATE for label, score in rows)
    tn = sum(label == "clean" and score < GATE for label, score in rows)
    fp = sum(label == "clean" and score >= GATE for label, score in rows)
    fn = sum(label == "sloppy" and score < GATE for label, score in rows)
    accuracy = safe_div(tp + tn, len(rows))
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    f1 = (None if precision is None or recall is None or precision + recall == 0
          else 2 * precision * recall / (precision + recall))
    balanced = (None if recall is None or specificity is None
                else (recall + specificity) / 2)
    return {
        "items": len(rows), "true_positive": tp, "true_negative": tn,
        "false_positive": fp, "false_negative": fn,
        "accuracy": rounded(accuracy), "accuracy_wilson_95_ci": wilson(tp + tn, len(rows)),
        "precision": rounded(precision), "recall": rounded(recall),
        "specificity": rounded(specificity), "f1": rounded(f1),
        "balanced_accuracy": rounded(balanced), "roc_auc": rounded(auc(rows)),
    }


def kappa(label_maps, ids):
    if len(label_maps) != 2 or not ids:
        return None
    a, b = label_maps
    observed = sum(a[item_id]["label"] == b[item_id]["label"] for item_id in ids) / len(ids)
    expected = sum(
        (sum(a[item_id]["label"] == label for item_id in ids) / len(ids))
        * (sum(b[item_id]["label"] == label for item_id in ids) / len(ids))
        for label in LABELS
    )
    return None if expected == 1 else (observed - expected) / (1 - expected)


def compute(manifest_path, label_paths):
    manifest = load_manifest(manifest_path)
    if len(label_paths) != 2:
        raise ContractError("exactly two independent label files are required")
    raters, label_maps = [], []
    for path in label_paths:
        rater, rows = load_labels(path, manifest)
        if rater in raters:
            raise ContractError("label files must name distinct raters")
        raters.append(rater)
        label_maps.append(rows)
    patterns = slopscore.load_patterns()
    scored = []
    consensus = {}
    for item in manifest["items"]:
        votes = [labels[item["id"]] for labels in label_maps]
        labels = {vote["label"] for vote in votes}
        agreed = next(iter(labels)) if len(labels) == 1 else "unresolved"
        if agreed == "borderline":
            agreed = "unresolved"
        score = slopscore.score_text(item["text"], patterns)["ai_likelihood"]
        scored.append({**item, "surface_score": score, "votes": votes,
                       "consensus": agreed})
        consensus[item["id"]] = agreed

    eligible = [row for row in scored if row["consensus"] in {"clean", "sloppy"}]
    metric_rows = [(row["consensus"], row["surface_score"]) for row in eligible]
    split_results = {}
    for split in ("dev", "test"):
        rows = [(row["consensus"], row["surface_score"]) for row in eligible
                if row["split"] == split]
        split_results[split] = binary_metrics(rows)

    methods = {}
    for method in sorted({row["method"] for row in scored}):
        rows = [row for row in scored if row["method"] == method]
        methods[method] = {
            "items": len(rows),
            "consensus_clean": sum(row["consensus"] == "clean" for row in rows),
            "consensus_sloppy": sum(row["consensus"] == "sloppy" for row in rows),
            "unresolved": sum(row["consensus"] == "unresolved" for row in rows),
            "mean_blind_severity": round(st.mean(
                vote["severity"] for row in rows for vote in row["votes"]), 2),
            "mean_surface_score": round(st.mean(row["surface_score"] for row in rows), 1),
        }

    ids = [row["id"] for row in manifest["items"]]
    exact_agreement = sum(len({labels[item_id]["label"] for labels in label_maps}) == 1
                          for item_id in ids)
    by_id = {row["id"]: row for row in scored}
    directions = {}
    for predictor_index, gold_index in ((0, 1), (1, 0)):
        name = f"{raters[predictor_index]}_to_{raters[gold_index]}"
        directions[name] = {}
        for split in ("all", "dev", "test"):
            eligible_ids = [item_id for item_id in ids
                            if label_maps[predictor_index][item_id]["label"]
                            in {"clean", "sloppy"}
                            and label_maps[gold_index][item_id]["label"]
                            in {"clean", "sloppy"}
                            and (split == "all" or by_id[item_id]["split"] == split)]
            contextual_rows = [
                (label_maps[gold_index][item_id]["label"],
                 GATE if label_maps[predictor_index][item_id]["label"] == "sloppy" else 0.0)
                for item_id in eligible_ids
            ]
            surface_rows = [
                (label_maps[gold_index][item_id]["label"], by_id[item_id]["surface_score"])
                for item_id in eligible_ids
            ]
            contextual = binary_metrics(contextual_rows)
            surface = binary_metrics(surface_rows)
            directions[name][split] = {
                "eligible_items": len(eligible_ids),
                "contextual": contextual,
                "surface_on_same_items": surface,
                "contextual_minus_surface_accuracy": (
                    None if contextual["accuracy"] is None or surface["accuracy"] is None
                    else round(contextual["accuracy"] - surface["accuracy"], 4)
                ),
            }
    held_out = [row["test"] for row in directions.values()]

    def mean_metric(section, metric):
        values = [row[section][metric] for row in held_out
                  if row[section][metric] is not None]
        return None if not values else round(st.mean(values), 4)

    contextual_test_accuracy = mean_metric("contextual", "accuracy")
    surface_test_accuracy = mean_metric("surface_on_same_items", "accuracy")
    contextual_ablation = {
        "field_accuracy": False,
        "design": ("Each blind rater acts once as the structured contextual reviewer "
                   "and once as the independent comparison label. Borderline calls "
                   "abstain; each direction is scored on the same eligible items."),
        "directions": directions,
        "held_out_test_mean": {
            "contextual_accuracy": contextual_test_accuracy,
            "surface_accuracy_on_same_items": surface_test_accuracy,
            "contextual_minus_surface_accuracy": (
                None if contextual_test_accuracy is None or surface_test_accuracy is None
                else round(contextual_test_accuracy - surface_test_accuracy, 4)
            ),
            "contextual_precision": mean_metric("contextual", "precision"),
            "contextual_recall": mean_metric("contextual", "recall"),
        },
        "limits": ("This estimates reproducibility between two blind LLM editorial "
                   "reviews. It is not an independent human accuracy estimate, and "
                   "the two directional samples share texts."),
    }
    manifest_bytes = Path(manifest_path).read_bytes()
    return {
        "result_kind": "blind_slop_quality_evaluation",
        "calibrated_field_accuracy": False,
        "source": {"manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                   "items": len(scored), "source_drafts": len({r["source_id"] for r in scored})},
        "labels": {"raters": raters, "consensus_items": len(eligible),
                   "unresolved_items": len(scored) - len(eligible),
                   "exact_agreement": round(exact_agreement / len(ids), 4),
                   "cohens_kappa": rounded(kappa(label_maps, ids))},
        "generic_surface_gate": GATE,
        "surface_meter": binary_metrics(metric_rows),
        "splits": split_results,
        "contextual_research_ablation": contextual_ablation,
        "methods": methods,
        "limits": ("Blind LLM-as-a-judge labels on a small clustered panel are not "
                   "independent human field labels. Method rows describe this panel; "
                   "surface metrics use consensus clean/sloppy items only."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--labels", action="append", default=[])
    parser.add_argument("--out", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = compute(args.manifest, args.labels)
        target = Path(args.out)
        if args.write:
            atomic_write_text(target, json.dumps(result, indent=1) + "\n")
        else:
            committed = read_json(target, "committed result")
            if committed != result:
                raise ContractError("committed quality result is stale")
        print(f"blind quality panel: {result['labels']['consensus_items']}/"
              f"{result['source']['items']} consensus clean/sloppy labels; "
              f"surface accuracy {result['surface_meter']['accuracy']}")
        return 0
    except ContractError as exc:
        print(f"quality evaluation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
