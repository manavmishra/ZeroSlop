#!/usr/bin/env python3
"""Probe Zero Slop's rule coverage against a pinned external tell taxonomy.

The AIStoryHub corpus is a list of words, phrases, and structural tells. It is
not labeled prose, so this script reports probe coverage, never accuracy,
precision, recall, or authorship. The source JSON is fetched only when a
maintainer passes --fetch, or read from an explicit local --source path.
"""
import argparse
import hashlib
import json
import math
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_PIN = HERE / "source.json"
DEFAULT_RESULT = HERE / "results.json"
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402
from safeio import atomic_write_text  # noqa: E402

REQUIRED_ENTRY_FIELDS = {
    "term": str,
    "category": str,
    "category_key": str,
    "confidence": str,
    "lifecycle": str,
    "strength_score": (int, float),
}
CONFIDENCE = {"red", "orange", "yellow"}
LIFECYCLE = {"hard_evidence", "live", "fading", "red_herring"}


def read_json(path):
    try:
        value = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def fetch(url, timeout):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "ZeroSlop-Corpus-Audit/2.4.3 "
                "(+https://github.com/manavmishra/ZeroSlop)"
            )
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise ValueError(f"cannot fetch pinned corpus: {exc}") from exc


def load_source(args, pin):
    if args.fetch:
        raw = fetch(pin["source_url"], args.timeout)
    else:
        try:
            raw = args.source.read_bytes()
        except OSError as exc:
            raise ValueError(f"cannot read source corpus: {exc}") from exc
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"source corpus is not valid JSON: {exc}") from exc
    return raw, document


def validate_pin(pin):
    required = {
        "source_url": str,
        "version": str,
        "generated": str,
        "entry_count": int,
        "sha256": str,
    }
    for key, kind in required.items():
        value = pin.get(key)
        if (not isinstance(value, kind) or isinstance(value, bool)
                or (isinstance(value, str) and not value.strip())):
            raise ValueError(f"pin field {key!r} is missing or invalid")
    if pin["entry_count"] < 1 or not re_full_sha256(pin["sha256"]):
        raise ValueError("pin entry_count or sha256 is invalid")


def re_full_sha256(value):
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_document(raw, document, pin):
    if not isinstance(document, dict):
        raise ValueError("source corpus must be a JSON object")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != pin["sha256"]:
        raise ValueError(
            "source hash differs from the pin; review the new corpus before updating source.json"
        )
    for key in ("version", "generated", "entry_count"):
        if document.get(key) != pin[key]:
            raise ValueError(f"source {key} differs from the pin")
    entries = document.get("entries")
    if not isinstance(entries, list) or len(entries) != pin["entry_count"]:
        raise ValueError("source entries do not match the pinned count")
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"entry {index} must be an object")
        for key, kind in REQUIRED_ENTRY_FIELDS.items():
            value = entry.get(key)
            if (not isinstance(value, kind) or isinstance(value, bool)
                    or (isinstance(value, str) and not value.strip())):
                raise ValueError(f"entry {index} field {key!r} is invalid")
        if not math.isfinite(entry["strength_score"]) or not 0 <= entry["strength_score"] <= 100:
            raise ValueError(f"entry {index} strength_score is invalid")
        if entry["confidence"] not in CONFIDENCE:
            raise ValueError(f"entry {index} confidence is unknown")
        if entry["lifecycle"] not in LIFECYCLE:
            raise ValueError(f"entry {index} lifecycle is unknown")
        identity = (entry["category_key"], entry["term"].casefold())
        if identity in seen:
            raise ValueError(f"duplicate category/term at entry {index}")
        seen.add(identity)
    return entries, digest


def probe_text(entry):
    example = entry.get("example")
    if isinstance(example, str) and example.strip():
        return example.strip(), "example"
    if (entry["category_key"] in {
            "words_and_phrases", "names_and_personas", "channel_and_assistant"
            } and "(" not in entry["term"]):
        return entry["term"].strip(), "literal_term"
    return None, None


def group_summary(rows, field):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[field]].append(row)
    return {
        key: {
            "testable": len(values),
            "surface_rule_hit": sum(value["surface_rule_hit"] for value in values),
            "surface_rule_hit_rate": round(
                100 * sum(value["surface_rule_hit"] for value in values) / len(values), 1
            ),
        }
        for key, values in sorted(grouped.items())
    }


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute(raw, document, pin):
    entries, digest = validate_document(raw, document, pin)
    data = slopscore.load_patterns()
    rows, misses = [], []
    for entry in entries:
        sample, probe_kind = probe_text(entry)
        if sample is None:
            continue
        result = slopscore.score_text(sample, data)
        hit = bool(result["hits"])
        row = {
            "category_key": entry["category_key"],
            "confidence": entry["confidence"],
            "lifecycle": entry["lifecycle"],
            "surface_rule_hit": hit,
            "probe_kind": probe_kind,
        }
        rows.append(row)
        if (not hit and entry["confidence"] == "red"
                and entry["lifecycle"] in {"live", "hard_evidence"}
                and entry["category_key"] != "names_and_personas"):
            misses.append((entry["strength_score"], entry["category_key"], entry["term"]))

    human_scores = []
    corpus_dir = ROOT / "data" / "corpus" / "must-not-flag"
    for path in sorted(corpus_dir.iterdir()):
        if (path.suffix.lower() not in {".txt", ".md"} or not path.is_file()
                or path.name.lower() == "readme.md"):
            continue
        human_scores.append(slopscore.score_text(path.read_text(), data)["ai_likelihood"])
    if not human_scores:
        raise ValueError("must-not-flag corpus is empty")

    covered = sum(row["surface_rule_hit"] for row in rows)
    result = {
        "audit_kind": "external_taxonomy_probe_coverage",
        "calibrated_accuracy": False,
        "source": {
            "name": pin.get("name"),
            "url": pin["source_url"],
            "version": pin["version"],
            "generated": pin["generated"],
            "entry_count": pin["entry_count"],
            "sha256": digest,
        },
        "zero_slop_taxonomy": {
            "patterns_sha256": file_sha256(ROOT / "data" / "patterns.json"),
            "learned_sha256": file_sha256(ROOT / "data" / "learned.json"),
        },
        "probe": {
            "definition": "Use the supplied example when present; otherwise use an unambiguous literal term in a lexical, persona, or channel category.",
            "testable_entries": len(rows),
            "surface_rule_hit": covered,
            "surface_rule_hit_rate": round(100 * covered / len(rows), 1),
            "by_confidence": group_summary(rows, "confidence"),
            "by_category": group_summary(rows, "category_key"),
            "by_lifecycle": group_summary(rows, "lifecycle"),
        },
        "false_positive_guard": {
            "documents": len(human_scores),
            "gate": 25,
            "passes": sum(score <= 25 for score in human_scores),
            "max_surface_score": max(human_scores),
        },
        "limitations": [
            "The source is a tell taxonomy, not labeled prose; coverage is not accuracy, precision, recall, quality, or authorship detection.",
            "A probe is covered when any Zero Slop rule fires on its supplied example or literal term; this does not establish one-to-one taxonomy equivalence.",
            "Persona names are intentionally not lexical convictions because real people can share them.",
            "Ambiguous vocabulary remains context-gated even when the external source labels it strongly.",
        ],
    }
    return result, sorted(misses, reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fetch", action="store_true", help="fetch the pinned public JSON")
    source.add_argument("--source", type=Path, help="read a previously downloaded JSON file")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="write the derived aggregate result")
    action.add_argument("--check", action="store_true", help="compare against the committed result")
    parser.add_argument("--pin", type=Path, default=DEFAULT_PIN)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--show-misses", type=int, default=12)
    args = parser.parse_args()
    try:
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise ValueError("--timeout must be a positive finite number")
        if args.show_misses < 0:
            raise ValueError("--show-misses must be non-negative")
        pin = read_json(args.pin)
        validate_pin(pin)
        raw, document = load_source(args, pin)
        fresh, misses = compute(raw, document, pin)
        resolved_output = args.output.resolve()
        protected = {args.pin.resolve()}
        if args.source:
            protected.add(args.source.resolve())
        if resolved_output in protected:
            raise ValueError("refusing to overwrite the pin or source corpus")
        if args.write:
            atomic_write_text(args.output, json.dumps(fresh, indent=1) + "\n")
        else:
            stored = read_json(args.output)
            if stored != fresh:
                print("AIStoryHub coverage result is stale; rerun with --write")
                return 1
        print(
            f"AIStoryHub v{pin['version']}: "
            f"{fresh['probe']['surface_rule_hit']}/{fresh['probe']['testable_entries']} "
            "testable probes produced a Zero Slop rule hit"
        )
        for strength, category, term in misses[:args.show_misses]:
            print(f"  review {strength:g} {category}: {term}")
        return 0
    except (ValueError, OSError) as exc:
        print(f"aistoryhub audit: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
