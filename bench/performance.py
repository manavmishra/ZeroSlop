#!/usr/bin/env python3
"""Measure local scorer and learning-loop performance with the CI fixtures."""
import argparse
import json
import os
import platform
import statistics as st
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus" / "must-not-flag"
OUTPUT = ROOT / "bench" / "performance-results.json"
sys.path.insert(0, str(ROOT / "scripts"))
import learn  # noqa: E402
import register  # noqa: E402
import slopscore  # noqa: E402
import contextual  # noqa: E402
from safeio import atomic_write_text  # noqa: E402


def timed(fn, repeats=3):
    values = []
    for _ in range(repeats):
        started = time.perf_counter()
        fn()
        values.append(time.perf_counter() - started)
    return values


def compute():
    data = slopscore.load_patterns()
    ordinary = (CORPUS / "technical-postmortem.txt").read_text()
    large = (CORPUS / "personal-essay.txt").read_text() * 200

    batch = timed(lambda: [slopscore.score_text(ordinary, data) for _ in range(1000)])
    long_doc = timed(lambda: slopscore.score_text(large, data))

    pathological = {}
    for label, value in {
        "single_character": "a" * 60000,
        "repeated_word": "the " * 12000,
        "repeated_dash": "— " * 6000,
        "newlines": "\n" * 30000,
    }.items():
        elapsed = timed(lambda value=value: slopscore.score_text(value, data), repeats=1)[0]
        pathological[label] = round(elapsed, 4)

    # The register pass runs on every draft the skill touches and was the one
    # local tool with no timing on record. It segments sentences and walks every
    # adjacent pair, so its cost scales with the document rather than with the
    # pattern table, and that is worth watching separately from the meter.
    register_batch = timed(lambda: [register.measure(ordinary) for _ in range(1000)])
    register_long = timed(lambda: register.measure(large))
    register_pathological = {}
    for label, value in {
        "single_character": "a" * 60000,
        "repeated_word": "the " * 12000,
        "no_sentence_terminator": "alpha beta gamma " * 12000,
        "all_sentence_terminators": ". " * 30000,
    }.items():
        elapsed = timed(lambda value=value: register.measure(value), repeats=1)[0]
        register_pathological[label] = round(elapsed, 4)

    old_observations = learn.OBS
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        produced, shipped = temp / "produced.md", temp / "shipped.md"
        produced.write_text("This puts wood behind the arrow on latency. " * 800)
        shipped.write_text("Latency dropped. " * 800)
        reflect_words = len(produced.read_text().split()) + len(shipped.read_text().split())
        learn.OBS = temp / "observations.json"
        try:
            reflect = timed(lambda: learn.reflect(
                str(produced), str(shipped), "performance-probe"), repeats=1)[0]
        finally:
            learn.OBS = old_observations

        contextual_text = "\n\n".join(
            f"Paragraph {index} records one specific operational fact."
            for index in range(2000)
        )
        contextual_draft = temp / "contextual.md"
        contextual_draft.write_text(contextual_text)
        packet = contextual.prepare(contextual_draft)
        contextual_review = temp / "contextual-review.json"
        contextual_review.write_text(json.dumps({
            "schema": 1,
            "source_sha256": packet["source_sha256"],
            "items": [{"paragraph_id": row["paragraph_id"],
                       "decision": "clear", "signals": []}
                      for row in packet["paragraphs"]],
        }))
        contextual_prepare = timed(lambda: contextual.prepare(contextual_draft))
        contextual_validate = timed(
            lambda: contextual.validate(contextual_draft, contextual_review)
        )

        retrieval_overlay = learn.empty_learned("performance")
        retrieval_overlay["fix_preferences"] = [
            {"source_span": f"stock framing phrase {index}",
             "preferred_fix": f"plain wording {index}", "seen_in_pairs": 3,
             "reasons": {"canned_framing": 3}, "genres": {"general": 3},
             "active": True}
            for index in range(5000)
        ]
        retrieval = timed(lambda: learn.retrieve_preferences(
            "stock framing phrase 4242 appears here", reason="canned_framing",
            genre="general", limit=5, learned=retrieval_overlay
        ))

    batch_median = st.median(batch)
    return {
        "result_kind": "local_performance_observation",
        "measured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "environment": {
            "platform": platform.system(),
            "architecture": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "python": platform.python_version(),
        },
        "scorer": {
            "batch_documents": 1000,
            "batch_repeats": len(batch),
            "batch_seconds": [round(value, 4) for value in batch],
            "median_batch_seconds": round(batch_median, 4),
            "median_documents_per_second": round(1000 / batch_median, 1),
            "median_milliseconds_per_document": round(1000 * batch_median / 1000, 2),
            "large_document_words": len(large.split()),
            "large_document_repeats": len(long_doc),
            "large_document_seconds": [round(value, 4) for value in long_doc],
            "median_large_document_seconds": round(st.median(long_doc), 4),
            "pathological_input_seconds": pathological,
        },
        "register": {
            "batch_documents": 1000,
            "batch_repeats": len(register_batch),
            "batch_seconds": [round(value, 4) for value in register_batch],
            "median_batch_seconds": round(st.median(register_batch), 4),
            "median_documents_per_second": round(1000 / st.median(register_batch), 1),
            "large_document_words": len(large.split()),
            "large_document_seconds": [round(value, 4) for value in register_long],
            "median_large_document_seconds": round(st.median(register_long), 4),
            "pathological_input_seconds": register_pathological,
        },
        "learning": {
            "reflect_diff_words": reflect_words,
            "reflect_seconds": round(reflect, 4),
            "retrieval_preferences": 5000,
            "retrieval_seconds": [round(value, 4) for value in retrieval],
            "median_retrieval_seconds": round(st.median(retrieval), 4),
        },
        "contextual_research": {
            "paragraphs": len(packet["paragraphs"]),
            "prepare_seconds": [round(value, 4) for value in contextual_prepare],
            "median_prepare_seconds": round(st.median(contextual_prepare), 4),
            "validate_seconds": [round(value, 4) for value in contextual_validate],
            "median_validate_seconds": round(st.median(contextual_validate), 4),
            "host_model_seconds": None,
        },
        "ci_thresholds": {
            "batch_1000_seconds_lt": 60,
            "large_document_seconds_lt": 30,
            "each_pathological_input_seconds_lt": 15,
            "register_batch_1000_seconds_lt": 60,
            "register_large_document_seconds_lt": 30,
            "reflect_seconds_lt": 30,
            "retrieval_5000_preferences_seconds_lt": 1,
            "contextual_2000_paragraph_prepare_seconds_lt": 3,
            "contextual_2000_paragraph_validate_seconds_lt": 3,
        },
        "limits": "Local wall-clock observation on one machine; useful for regression and capacity planning, not a universal throughput guarantee. Contextual timings cover local packet preparation and validation only, not host-model review latency.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = compute()
    if args.write:
        atomic_write_text(OUTPUT, json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
