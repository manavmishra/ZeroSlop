#!/usr/bin/env python3
"""Replay the private maintainer corpus without committing its source prose."""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("results.json")
sys.path.insert(0, str(ROOT / "scripts"))
import register  # noqa: E402
import slopscore  # noqa: E402
from safeio import atomic_write_text  # noqa: E402

DOC_URL = (
    "https://docs.google.com/document/d/"
    "1JT32uRH_HsQavHOfWnrrZNiaBRC60d9r19PX5fSIoW8/edit?tab=t.0"
)
ITEM = re.compile(r"(?m)^\s*(\d+)\\?\)\s*")


def _documents(source):
    parts = ITEM.split(source)
    documents = []
    for index in range(1, len(parts), 2):
        identifier, body = int(parts[index]), parts[index + 1].strip()
        if body:
            documents.append((identifier, body))
    identifiers = [identifier for identifier, _body in documents]
    if identifiers != list(range(1, len(documents) + 1)):
        raise ValueError(f"corpus item numbers are not contiguous: {identifiers}")
    return documents


def _rendered_prose(markdown):
    # Google Docs' Markdown export escapes punctuation that is visible as plain
    # punctuation in the document. Score what the reader sees, not the export
    # syntax, and keep link labels while removing their destinations.
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", markdown)
    value = re.sub(r"\\([\\`*_{}\[\]()#+.!-])", r"\1", value)
    return re.sub(r"[ \t]+$", "", value, flags=re.M)


def evaluate_text(source, *, version):
    data = slopscore.load_patterns()
    rows = []
    for identifier, markdown in _documents(source):
        prose = _rendered_prose(markdown)
        score = slopscore.score_text(prose, data)
        reading = register.measure(prose)
        over = [key for key, _value, _budget, ok in register.verdicts(reading) if not ok]
        rows.append({
            "id": identifier,
            "words": score["n_words"],
            "writing_score": score["ai_likelihood"],
            "findings": sorted({hit["name"] for hit in score["hits"]}),
            "reading_checks_over_budget": over,
        })
    scores = [row["writing_score"] for row in rows]
    gate = 25.0
    return {
        "result_kind": "private_maintainer_regression",
        "calibrated_accuracy": False,
        "source": {
            "document_id": "1JT32uRH_HsQavHOfWnrrZNiaBRC60d9r19PX5fSIoW8",
            "sha256": hashlib.sha256(source.encode()).hexdigest(),
            "documents": len(rows),
            "source_committed": False,
        },
        "scorer": {
            "version": version,
            "slopscore_sha256": hashlib.sha256((ROOT / "scripts" / "slopscore.py").read_bytes()).hexdigest(),
            "patterns_sha256": hashlib.sha256((ROOT / "data" / "patterns.json").read_bytes()).hexdigest(),
            "generic_gate": gate,
        },
        "summary": {
            "mean_writing_score": round(sum(scores) / len(scores), 1) if scores else None,
            "at_or_above_generic_gate": sum(value >= gate for value in scores),
            "documents_with_reading_findings": sum(bool(row["reading_checks_over_budget"])
                                                   for row in rows),
        },
        "items": rows,
        "limits": (
            "Maintainer-curated examples with no per-item rubric or clean controls. "
            "This is a private drift and missed-case review, not accuracy or field validation."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    default = os.environ.get(
        "ZERO_SLOP_INTERNAL_CORPUS",
        str(Path.home() / ".zero-slop" / "evals" / "slop-examples.md"),
    )
    parser.add_argument("--source", default=default)
    parser.add_argument("--out", default=str(OUT))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    source_path, out_path = Path(args.source), Path(args.out)
    try:
        source = source_path.read_text()
        version = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())["version"]
        report = evaluate_text(source, version=version)
        rendered = json.dumps(report, indent=1) + "\n"
        if args.check:
            if not out_path.exists() or out_path.read_text() != rendered:
                print("private corpus result drifted; review it, then rerun with --write")
                return 1
            print(
                f"private corpus: {report['source']['documents']} documents; "
                f"source {report['source']['sha256'][:12]}; result current"
            )
            return 0
        if args.write:
            atomic_write_text(out_path, rendered)
            print(f"wrote {out_path.relative_to(ROOT)} without source prose")
            return 0
        print(rendered, end="")
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"private corpus: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
