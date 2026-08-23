#!/usr/bin/env python3
"""Prepare and validate evidence-bound contextual reviews for release research.

This script never calls a model and never changes Zero Slop's surface score. It
turns a draft into stable paragraph IDs, then validates a host model's structured
review against the exact source bytes and quoted evidence.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCHEMA = 1
MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_REVIEW_BYTES = 2 * 1024 * 1024
MAX_PARAGRAPHS = 10000
MAX_SIGNALS_PER_PARAGRAPH = 8

SIGNALS = {
    "hollow_substance": "The passage occupies space without making a useful claim.",
    "semantic_redundancy": "The passage repeats meaning already present nearby.",
    "vague_reference": "A referent, actor, mechanism, or source is needlessly vague.",
    "canned_framing": "The argument follows a stock reveal, contrast, or summary shape.",
    "genre_mismatch": "The register or form does not fit the stated publication context.",
    "local_repetition": "Words, openings, or sentence structures recur mechanically.",
    "unsupported_attribution": "The passage invokes unnamed evidence or authority.",
    "reader_process_leak": "Editorial or evaluation machinery leaks into reader-facing prose.",
}
DECISIONS = {"clear", "flag", "abstain"}
SEVERITIES = {"low", "medium", "high"}
ACTIONS = {"repair", "cut", "rebuild", "ask_for_substance"}


class ContractError(ValueError):
    """A review or source failed a bounded, user-facing contract check."""


def read_bytes(path, limit, label):
    source = Path(path)
    if not source.is_file():
        raise ContractError(f"{label} is not a readable file: {source}")
    try:
        size = source.stat().st_size
        if size > limit:
            raise ContractError(f"{label} exceeds the {limit}-byte limit")
        raw = source.read_bytes()
    except OSError as exc:
        raise ContractError(f"cannot read {label}: {exc}") from exc
    if len(raw) > limit:
        raise ContractError(f"{label} exceeds the {limit}-byte limit")
    return raw


def read_text(path):
    raw = read_bytes(path, MAX_SOURCE_BYTES, "draft")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("draft must be UTF-8 text") from exc
    if not text.strip():
        raise ContractError("draft contains no text")
    return raw, text


def is_structured_line(line):
    stripped = line.lstrip()
    if not stripped:
        return False
    if stripped.startswith(("#", ">", "|")):
        return True
    if line.startswith(("    ", "\t")):
        return True
    if re.fullmatch(r"\s*[-:| ]{3,}\s*", line):
        return True
    return False


def prose_paragraphs(text):
    """Return running-text paragraphs while preserving their exact words.

    Markdown headings, fenced or indented code, block quotations, and tables are
    deliberately omitted. The host editor still preserves those structures under
    the main skill contract; they are simply not contextual-prose probes.
    """
    paragraphs, current = [], []
    fence = None

    def flush():
        if current:
            paragraph = " ".join(part.strip() for part in current if part.strip())
            if paragraph:
                paragraphs.append(paragraph)
            current.clear()

    for line in text.splitlines():
        stripped = line.lstrip()
        fence_match = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_match and fence is None:
            flush()
            fence = fence_match.group(1)
            continue
        if fence is not None:
            if (fence_match and fence_match.group(1)[0] == fence[0]
                    and len(fence_match.group(1)) >= len(fence)):
                fence = None
            continue
        if not stripped:
            flush()
            continue
        if is_structured_line(line):
            flush()
            continue
        current.append(line)
    flush()
    if len(paragraphs) > MAX_PARAGRAPHS:
        raise ContractError(f"draft has more than {MAX_PARAGRAPHS} prose paragraphs")
    return paragraphs


def prepare(path):
    raw, text = read_text(path)
    paragraphs = prose_paragraphs(text)
    if not paragraphs:
        raise ContractError("draft contains no reviewable prose paragraphs")
    return {
        "schema": SCHEMA,
        "result_kind": "contextual_research_packet",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "affects_surface_score": False,
        "paragraphs": [
            {"paragraph_id": f"p{index:04d}", "text": paragraph}
            for index, paragraph in enumerate(paragraphs, 1)
        ],
        "contract": {
            "decisions": sorted(DECISIONS),
            "signals": SIGNALS,
            "severities": sorted(SEVERITIES),
            "actions": sorted(ACTIONS),
            "evidence": "Every flag must quote an exact contiguous span from its paragraph.",
            "abstention": "Use abstain when a judgment would require missing context.",
        },
    }


def load_review(path):
    raw = read_bytes(path, MAX_REVIEW_BYTES, "review")
    try:
        review = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("review must be valid UTF-8 JSON") from exc
    return review


def exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ContractError(f"{label} must contain exactly: {', '.join(expected)}")


def validate_signal(signal, paragraph, label):
    exact_keys(signal, ("signal", "severity", "quote", "reason", "action"), label)
    if signal["signal"] not in SIGNALS:
        raise ContractError(f"{label} has an unknown signal")
    if signal["severity"] not in SEVERITIES:
        raise ContractError(f"{label} has an unknown severity")
    if signal["action"] not in ACTIONS:
        raise ContractError(f"{label} has an unknown action")
    quote = signal["quote"]
    reason = signal["reason"]
    if not isinstance(quote, str) or not quote.strip() or len(quote) > 500:
        raise ContractError(f"{label} quote must be 1-500 characters")
    if quote not in paragraph:
        raise ContractError(f"{label} quote is not an exact span in its paragraph")
    if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 500:
        raise ContractError(f"{label} reason must be 10-500 characters")


def validate(path, review_path):
    packet = prepare(path)
    review = load_review(review_path)
    exact_keys(review, ("schema", "source_sha256", "items"), "review")
    if review["schema"] != SCHEMA:
        raise ContractError(f"unsupported review schema: {review['schema']!r}")
    if review["source_sha256"] != packet["source_sha256"]:
        raise ContractError("review source hash does not match the current draft")
    if not isinstance(review["items"], list):
        raise ContractError("review items must be a list")

    source = {row["paragraph_id"]: row["text"] for row in packet["paragraphs"]}
    seen, evidence, counts = set(), [], Counter()
    abstentions = 0
    for index, item in enumerate(review["items"], 1):
        label = f"review item {index}"
        if not isinstance(item, dict):
            raise ContractError(f"{label} must be an object")
        allowed = {"paragraph_id", "decision", "signals"}
        if item.get("decision") == "abstain":
            allowed.add("reason")
        if set(item) != allowed:
            raise ContractError(f"{label} contains missing or unexpected fields")
        paragraph_id = item.get("paragraph_id")
        if paragraph_id not in source or paragraph_id in seen:
            raise ContractError(f"{label} has an unknown or duplicate paragraph_id")
        seen.add(paragraph_id)
        decision = item.get("decision")
        signals = item.get("signals")
        if decision not in DECISIONS or not isinstance(signals, list):
            raise ContractError(f"{label} has an invalid decision or signals list")
        if len(signals) > MAX_SIGNALS_PER_PARAGRAPH:
            raise ContractError(f"{label} has too many signals")
        if decision == "flag" and not signals:
            raise ContractError(f"{label} flags a paragraph without evidence")
        if decision != "flag" and signals:
            raise ContractError(f"{label} supplies signals without a flag decision")
        if decision == "abstain":
            reason = item.get("reason")
            if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 500:
                raise ContractError(f"{label} abstention reason must be 10-500 characters")
            abstentions += 1
        for signal_index, signal in enumerate(signals, 1):
            signal_label = f"{label} signal {signal_index}"
            validate_signal(signal, source[paragraph_id], signal_label)
            counts[signal["signal"]] += 1
            evidence.append({"paragraph_id": paragraph_id, **signal})

    if seen != set(source):
        missing = sorted(set(source) - seen)
        raise ContractError(f"review omits {len(missing)} paragraph(s): {', '.join(missing[:5])}")
    return {
        "schema": SCHEMA,
        "result_kind": "contextual_research_review",
        "source_sha256": packet["source_sha256"],
        "affects_surface_score": False,
        "reviewed_paragraphs": len(source),
        "flagged_paragraphs": len({row["paragraph_id"] for row in evidence}),
        "abstentions": abstentions,
        "signals": dict(sorted(counts.items())),
        "evidence": evidence,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", metavar="DRAFT")
    mode.add_argument("--validate", nargs=2, metavar=("DRAFT", "REVIEW"))
    parser.add_argument("--json", action="store_true",
                        help="print machine-readable validation output")
    args = parser.parse_args()
    try:
        if args.prepare:
            if args.json:
                parser.error("--json is implicit with --prepare")
            print(json.dumps(prepare(args.prepare), indent=1))
            return 0
        result = validate(*args.validate)
        if args.json:
            print(json.dumps(result, indent=1))
        else:
            print(f"contextual review: {result['flagged_paragraphs']}/"
                  f"{result['reviewed_paragraphs']} paragraph(s) flagged; "
                  f"{result['abstentions']} abstention(s)")
            for row in result["evidence"]:
                print(f"  {row['paragraph_id']} {row['signal']}: {row['quote']!r}")
            print("  research evidence only; the 0-to-100 surface score is unchanged")
        return 0
    except ContractError as exc:
        print(f"contextual: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
