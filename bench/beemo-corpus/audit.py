#!/usr/bin/env python3
"""Audit Zero Slop's surface meter on Beemo's paired human-edit records."""
import argparse
import hashlib
import json
import statistics as st
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE = HERE / "source.json"
RESULT = HERE / "results.json"
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402
from safeio import atomic_write_text  # noqa: E402

API = "https://huggingface.co/api/datasets/{dataset}"
ROWS = "https://datasets-server.huggingface.co/rows"
FIELDS = ("model_output", "human_edits", "human_output")
LABELS = {
    "model_output": "Raw model output",
    "human_edits": "Expert human edit",
    "human_output": "Independent human answer",
}
GATE = 25.0


def fetch_json(url, attempts=3):
    request = urllib.request.Request(url, headers={"User-Agent": "ZeroSlop-audit/1"})
    error = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (OSError, ValueError) as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(0.25 * (attempt + 1))
    raise RuntimeError(f"could not fetch {url}: {error}")


def load_pin():
    pin = json.loads(SOURCE.read_text())
    required = {"dataset", "revision", "config", "split", "expected_rows",
                "dataset_url", "paper_url", "license_note", "purpose"}
    if set(pin) != required or len(pin["revision"]) != 40:
        raise ValueError("source.json has an invalid contract")
    if not isinstance(pin["expected_rows"], int) or pin["expected_rows"] <= 0:
        raise ValueError("source.json expected_rows must be positive")
    return pin


def fetch_rows(pin):
    metadata = fetch_json(API.format(dataset=pin["dataset"]))
    if metadata.get("sha") != pin["revision"]:
        raise RuntimeError(
            f"dataset revision moved: pinned {pin['revision']}, current {metadata.get('sha')}"
        )
    rows, offset, total = [], 0, None
    while total is None or offset < total:
        query = urllib.parse.urlencode({
            "dataset": pin["dataset"], "config": pin["config"],
            "split": pin["split"], "offset": offset, "length": 100,
        })
        page = fetch_json(f"{ROWS}?{query}")
        page_total = page.get("num_rows_total")
        if not isinstance(page_total, int) or page_total <= 0:
            raise ValueError("dataset server returned an invalid row count")
        if total is None:
            total = page_total
        elif page_total != total:
            raise ValueError("dataset row count changed during pagination")
        batch = page.get("rows")
        if not isinstance(batch, list) or not batch:
            raise ValueError(f"dataset server returned no rows at offset {offset}")
        for item in batch:
            if item.get("row_idx") != len(rows):
                raise ValueError("dataset rows are missing, duplicated, or out of order")
            if item.get("truncated_cells"):
                raise ValueError(f"dataset server truncated row {item.get('row_idx')}")
            row = item.get("row")
            if not isinstance(row, dict) or any(not isinstance(row.get(field), str)
                                                or not row[field].strip()
                                                for field in FIELDS):
                raise ValueError(f"dataset row {item.get('row_idx')} is malformed")
            rows.append(row)
        offset = len(rows)
    if total != pin["expected_rows"] or len(rows) != total:
        raise ValueError(
            f"dataset has {len(rows)}/{total} rows; pin expects {pin['expected_rows']}"
        )
    return metadata, rows


def summarize(values):
    return {
        "documents": len(values),
        "mean_surface_score": round(st.mean(values), 1),
        "median_surface_score": round(st.median(values), 1),
        "at_or_above_generic_gate": sum(value >= GATE for value in values),
        "at_or_above_generic_gate_pct": round(
            100 * sum(value >= GATE for value in values) / len(values), 1
        ),
    }


def compute(pin, metadata, rows):
    patterns = slopscore.load_patterns()
    scores = {field: [] for field in FIELDS}
    categories = {}
    fingerprint = hashlib.sha256()
    for index, row in enumerate(rows):
        record = {
            "index": index,
            "id": str(row.get("id", "")),
            "prompt_id": str(row.get("prompt_id", "")),
            "model": str(row.get("model", "")),
            "category": str(row.get("category", "")),
            **{field: row[field] for field in FIELDS},
        }
        fingerprint.update(json.dumps(record, sort_keys=True, ensure_ascii=False,
                                      separators=(",", ":")).encode())
        category = record["category"] or "unknown"
        categories[category] = categories.get(category, 0) + 1
        for field in FIELDS:
            scores[field].append(
                slopscore.score_text(row[field], patterns)["ai_likelihood"]
            )
    raw, edited = scores["model_output"], scores["human_edits"]
    reductions = [before - after for before, after in zip(raw, edited)]
    return {
        "result_kind": "external_paired_edit_surface_audit",
        "calibrated_accuracy": False,
        "source": {
            "dataset": pin["dataset"],
            "revision": pin["revision"],
            "last_modified": metadata.get("lastModified"),
            "rows": len(rows),
            "content_sha256": fingerprint.hexdigest(),
            "license_note": pin["license_note"],
        },
        "generic_surface_gate": GATE,
        "groups": {
            field: {"label": LABELS[field], **summarize(scores[field])}
            for field in FIELDS
        },
        "paired_model_to_expert_edit": {
            "pairs": len(reductions),
            "mean_score_reduction": round(st.mean(reductions), 1),
            "median_score_reduction": round(st.median(reductions), 1),
            "lower_after_edit": sum(delta > 0 for delta in reductions),
            "lower_after_edit_pct": round(
                100 * sum(delta > 0 for delta in reductions) / len(reductions), 1
            ),
            "unchanged": sum(delta == 0 for delta in reductions),
            "higher_after_edit": sum(delta < 0 for delta in reductions),
        },
        "categories": dict(sorted(categories.items())),
        "limits": (
            "Beemo labels provenance and editing history, not slop or writing quality. "
            "The generic Zero Slop surface gate is not tuned to these task categories. "
            "Results do not measure semantic fidelity, factual accuracy, authorship "
            "detection, or field accuracy."
        ),
    }


def validate(result, pin):
    if result.get("result_kind") != "external_paired_edit_surface_audit":
        raise ValueError("results.json has the wrong result kind")
    if result.get("calibrated_accuracy") is not False:
        raise ValueError("Beemo audit must not claim calibrated accuracy")
    source = result.get("source", {})
    if (source.get("revision") != pin["revision"]
            or source.get("rows") != pin["expected_rows"]
            or len(source.get("content_sha256", "")) != 64):
        raise ValueError("results.json does not match the source pin")
    for field in FIELDS:
        if result.get("groups", {}).get(field, {}).get("documents") != pin["expected_rows"]:
            raise ValueError(f"results.json has an invalid {field} count")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="fetch the pinned public rows")
    parser.add_argument("--write", action="store_true", help="write a freshly fetched result")
    parser.add_argument("--check", action="store_true", help="verify the committed result")
    args = parser.parse_args()
    if args.write and not args.fetch:
        parser.error("--write requires --fetch")
    if not args.write and not args.check:
        parser.error("choose --check or --write")
    pin = load_pin()
    if args.fetch:
        metadata, rows = fetch_rows(pin)
        fresh = compute(pin, metadata, rows)
        validate(fresh, pin)
        if args.write:
            atomic_write_text(RESULT, json.dumps(fresh, indent=1) + "\n")
        if args.check:
            committed = json.loads(RESULT.read_text())
            validate(committed, pin)
            if committed != fresh:
                raise SystemExit("Beemo audit is stale; run with --fetch --write and review")
        result = fresh
    else:
        result = json.loads(RESULT.read_text())
        validate(result, pin)
    groups = result["groups"]
    pair = result["paired_model_to_expert_edit"]
    print(f"Beemo {result['source']['rows']} paired records at {result['source']['revision'][:12]}")
    for field in FIELDS:
        row = groups[field]
        print(f"  {row['label']:<25} mean {row['mean_surface_score']:>5.1f}  "
              f">= {GATE:g}: {row['at_or_above_generic_gate']:>4}/{row['documents']}")
    print(f"  expert edit lowered the score in {pair['lower_after_edit']}/"
          f"{pair['pairs']} pairs ({pair['lower_after_edit_pct']:.1f}%)")
    print("  provenance/edit-history audit only; not slop accuracy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
