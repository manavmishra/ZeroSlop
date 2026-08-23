#!/usr/bin/env python3
"""Audit the current Zero Slop scorer on every pinned RAID+ generation."""
import argparse
import hashlib
import json
import statistics as st
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / "source.json"
RESULT = HERE / "results.json"
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402
from safeio import atomic_write_text  # noqa: E402

API = "https://huggingface.co/api/datasets/{dataset}"
ROWS = "https://datasets-server.huggingface.co/rows"
GATE = 25.0
PAGE_SIZE = 100
PAGE_DELAY_SECONDS = 1.05


def fetch_json(url, attempts=8):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "ZeroSlop-RAID-Plus-audit/2.5.5 "
                "(+https://github.com/manavmishra/ZeroSlop)"
            )
        },
    )
    error = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            error = exc
            if exc.code != 429 or attempt + 1 == attempts:
                break
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            time.sleep(min(delay, 30))
        except (OSError, ValueError) as exc:
            error = exc
            if attempt + 1 == attempts:
                break
            time.sleep(min(0.5 * (attempt + 1), 3))
    raise RuntimeError(f"could not fetch {url}: {error}")


def load_pin():
    pin = json.loads(SOURCE.read_text())
    required = {
        "dataset", "revision", "config", "split", "expected_rows",
        "expected_models", "dataset_url", "project_url", "license", "purpose",
    }
    if set(pin) != required or not isinstance(pin["revision"], str) \
            or len(pin["revision"]) != 40:
        raise ValueError("source.json has an invalid contract")
    if not isinstance(pin["expected_rows"], int) or pin["expected_rows"] <= 0:
        raise ValueError("source.json expected_rows must be positive")
    models = pin["expected_models"]
    if not isinstance(models, dict) or not models \
            or any(not isinstance(name, str) or not name
                   or not isinstance(count, int) or count <= 0
                   for name, count in models.items()) \
            or sum(models.values()) != pin["expected_rows"]:
        raise ValueError("source.json expected_models is invalid")
    return pin


def fetch_rows(pin):
    metadata = fetch_json(API.format(dataset=pin["dataset"]))
    if metadata.get("sha") != pin["revision"]:
        raise RuntimeError(
            f"dataset revision moved: pinned {pin['revision']}, "
            f"current {metadata.get('sha')}"
        )
    rows, offset, total = [], 0, None
    while total is None or offset < total:
        query = urllib.parse.urlencode({
            "dataset": pin["dataset"], "config": pin["config"],
            "split": pin["split"], "offset": offset, "length": PAGE_SIZE,
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
            if not isinstance(row, dict):
                raise ValueError(f"dataset row {item.get('row_idx')} is malformed")
            rows.append(row)
        offset = len(rows)
        if offset < total:
            time.sleep(PAGE_DELAY_SECONDS)
    if total != pin["expected_rows"] or len(rows) != total:
        raise ValueError(
            f"dataset has {len(rows)}/{total} rows; pin expects {pin['expected_rows']}"
        )
    return metadata, rows


def summarize(values):
    if not values:
        raise ValueError("cannot summarize an empty score group")
    quartiles = st.quantiles(values, n=4, method="inclusive")
    above = sum(value >= GATE for value in values)
    return {
        "documents": len(values),
        "mean_writing_score": round(st.mean(values), 1),
        "median_writing_score": round(st.median(values), 1),
        "middle_50_pct_range": [round(quartiles[0], 1), round(quartiles[2], 1)],
        "at_or_above_generic_gate": above,
        "at_or_above_generic_gate_pct": round(100 * above / len(values), 1),
    }


def compute(pin, metadata, rows):
    patterns = slopscore.load_patterns()
    scores_by_model = defaultdict(list)
    scores_by_domain = defaultdict(list)
    source_models = Counter()
    failures = Counter()
    fingerprint = hashlib.sha256()
    required = {
        "generated_at", "max_tokens", "prompt_id", "dataset", "domain",
        "new_model", "generation", "error", "new_model_id", "prompt",
        "temperature",
    }
    for index, row in enumerate(rows):
        if not required.issubset(row):
            raise ValueError(f"dataset row {index} is missing required fields")
        model, domain = row["new_model"], row["domain"]
        if model not in pin["expected_models"] or not isinstance(domain, str) or not domain:
            raise ValueError(f"dataset row {index} has an unknown model or domain")
        source_models[model] += 1
        record = {key: row[key] for key in sorted(required)}
        fingerprint.update(json.dumps(
            record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode())
        text = row["generation"]
        if row["error"] is not None or not isinstance(text, str) or not text.strip():
            failures[model] += 1
            continue
        score = slopscore.score_text(
            text, patterns, formal=(domain == "abstracts")
        )["ai_likelihood"]
        scores_by_model[model].append(score)
        scores_by_domain[domain].append(score)
    if dict(sorted(source_models.items())) != dict(sorted(pin["expected_models"].items())):
        raise ValueError("dataset model counts do not match the source pin")
    scored = sum(len(values) for values in scores_by_model.values())
    return {
        "result_kind": "current_model_surface_audit",
        "calibrated_accuracy": False,
        "source": {
            "dataset": pin["dataset"],
            "revision": pin["revision"],
            "last_modified": metadata.get("lastModified"),
            "rows": len(rows),
            "scored_rows": scored,
            "failed_or_empty_rows": len(rows) - scored,
            "model_rows": dict(sorted(source_models.items())),
            "content_sha256": fingerprint.hexdigest(),
            "license": pin["license"],
        },
        "scorer": {
            "version": "2.5.5",
            "patterns_sha256": hashlib.sha256(
                (ROOT / "data" / "patterns.json").read_bytes()
            ).hexdigest(),
            "learned_sha256": hashlib.sha256(
                (ROOT / "data" / "learned.json").read_bytes()
            ).hexdigest(),
            "generic_gate": GATE,
            "formal_domains": ["abstracts"],
        },
        "overall": summarize([
            value for values in scores_by_model.values() for value in values
        ]),
        "models": {
            model: {**summarize(scores_by_model[model]), "failed_or_empty": failures[model]}
            for model in sorted(pin["expected_models"])
        },
        "domains": {
            domain: summarize(values) for domain, values in sorted(scores_by_domain.items())
        },
        "limits": (
            "RAID+ supplies machine provenance, not slop-quality labels. These score "
            "distributions are not editorial quality, authorship accuracy, precision, "
            "recall, or a comparison with human writing."
        ),
    }


def validate(result, pin):
    if result.get("result_kind") != "current_model_surface_audit" \
            or result.get("calibrated_accuracy") is not False:
        raise ValueError("results.json has the wrong result contract")
    source = result.get("source", {})
    if source.get("revision") != pin["revision"] \
            or source.get("rows") != pin["expected_rows"] \
            or source.get("model_rows") != pin["expected_models"] \
            or not isinstance(source.get("scored_rows"), int) \
            or source["scored_rows"] <= 0 \
            or source.get("failed_or_empty_rows") != pin["expected_rows"] - source["scored_rows"] \
            or len(source.get("content_sha256", "")) != 64:
        raise ValueError("results.json does not match the source pin")
    models = result.get("models", {})
    if set(models) != set(pin["expected_models"]):
        raise ValueError("results.json model set is invalid")
    for model, expected in pin["expected_models"].items():
        row = models[model]
        if row.get("documents", 0) + row.get("failed_or_empty", 0) != expected:
            raise ValueError(f"results.json has an invalid {model} count")
    if result.get("overall", {}).get("documents") != source["scored_rows"]:
        raise ValueError("results.json overall count is invalid")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="fetch every pinned public row")
    parser.add_argument("--write", action="store_true", help="write a freshly fetched result")
    parser.add_argument("--check", action="store_true", help="verify the committed result")
    args = parser.parse_args()
    if args.write and not args.fetch:
        parser.error("--write requires --fetch")
    if not args.write and not args.check:
        parser.error("choose --check or --write")
    try:
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
                    raise ValueError(
                        "committed result is stale; rerun with --fetch --write and review"
                    )
            result = fresh
        else:
            result = json.loads(RESULT.read_text())
            validate(result, pin)
        print(f"RAID+ {result['source']['scored_rows']}/{result['source']['rows']} "
              f"generations scored at {result['source']['revision'][:12]}")
        for model, row in result["models"].items():
            print(f"  {model:<16} mean {row['mean_writing_score']:>5.1f}  "
                  f">= {GATE:g}: {row['at_or_above_generic_gate']:>4}/"
                  f"{row['documents']}")
        print("  current-model provenance audit only; not slop accuracy")
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError,
            RuntimeError, ValueError) as exc:
        print(f"RAID+ audit: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
