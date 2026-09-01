#!/usr/bin/env python3
"""Precision and recall for the antithesis-pair detector, on a labelled set.

The register report budgets this family by frequency, so the count has to be
right before the budget means anything. Before this corpus existed the detector
had only two kinds of evidence: it fired on four hand-picked anchors, and it
stayed silent on the certified-human corpus. Neither is a recall measurement.

Limits, stated rather than implied. These 58 pairs are hand-authored and
hand-labelled by the maintainer, not drawn from a sampled population and not
independently adjudicated. The numbers describe agreement with one reader's
labels on constructed examples. They are a regression floor, not field accuracy.

Two shapes are labelled `antithesis` that the detector is not expected to
reach, and they are counted against recall rather than excused:
  subject-swap   -- references/tells.md calls it a judgment call outright.
  weak-isocolon  -- "A meter reports a number. A reader reports a feeling." is
                    identical to the ordinary "The report lists every vendor.
                    The appendix lists every contract." on every lexical
                    statistic: same lengths, one shared word, 0.33 overlap.
                    Only semantic opposition separates them.
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import register  # noqa: E402

OUT_OF_REACH = {"subject-swap", "weak-isocolon"}


def evaluate() -> dict:
    corpus = json.loads((HERE / "corpus.json").read_text())
    tp = fn = fp = tn = 0
    missed, wrong = [], []
    for item in corpus:
        fired = bool(register.antithesis_pairs(item["text"]))
        if item["label"] == "antithesis":
            if fired:
                tp += 1
            else:
                fn += 1
                missed.append(item)
        else:
            if fired:
                fp += 1
                wrong.append(item)
            else:
                tn += 1
    in_reach = [i for i in corpus
                if i["label"] == "antithesis" and i["shape"] not in OUT_OF_REACH]
    in_reach_hit = sum(1 for i in in_reach if register.antithesis_pairs(i["text"]))
    return {
        "schema": 1,
        "items": len(corpus),
        "antithesis_items": tp + fn,
        "ordinary_items": fp + tn,
        "true_positives": tp, "false_negatives": fn,
        "false_positives": fp, "true_negatives": tn,
        "recall": round(tp / max(1, tp + fn), 4),
        "precision": round(tp / max(1, tp + fp), 4),
        "specificity": round(tn / max(1, tn + fp), 4),
        "in_reach_items": len(in_reach),
        "in_reach_recall": round(in_reach_hit / max(1, len(in_reach)), 4),
        "missed": [i["id"] for i in missed],
        "false_positive_ids": [i["id"] for i in wrong],
        "limits": ("hand-authored and hand-labelled by the maintainer; a regression "
                   "floor for the detector, not field accuracy and not an "
                   "independently adjudicated corpus"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if the committed result is stale")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    results_path = HERE / "results.json"
    if args.write:
        results_path.write_text(json.dumps(result, indent=2) + "\n")
        print(f"wrote {results_path}")
        return 0
    if args.check:
        if not results_path.exists():
            print("antithesis: results.json is missing", file=sys.stderr)
            return 2
        committed = json.loads(results_path.read_text())
        if committed != result:
            print("antithesis: results.json is stale; rerun with --write",
                  file=sys.stderr)
            return 2
    print(f"antithesis: {result['items']} labelled pairs; "
          f"recall {result['recall']:.1%} ({result['in_reach_recall']:.1%} on the "
          f"{result['in_reach_items']} in reach), precision {result['precision']:.1%}, "
          f"specificity {result['specificity']:.1%}")
    if result["missed"]:
        print("  missed: " + ", ".join(result["missed"]))
    if result["false_positive_ids"]:
        print("  false positives: " + ", ".join(result["false_positive_ids"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
