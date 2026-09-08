#!/usr/bin/env python3
"""Turn a slopscore JSON report into GitHub Actions annotations, outputs, and a summary.

Kept out of action.yml so it can be tested like ordinary code rather than
reviewed as an inline heredoc.

    python3 scripts/gha_report.py --gate 25 --report report.json

Writes to $GITHUB_OUTPUT and $GITHUB_STEP_SUMMARY when those are set, and prints
annotations to stdout. Exit status is 0 unless the report cannot be read; the
gate verdict travels through the `passed` output so the caller decides whether a
score above the gate should fail the build.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SUMMARY_ROWS = 50


def normalise(report: dict, scored_path: str = "") -> list[dict]:
    """Return one row per document for both --batch and single-file reports.

    A single-file report carries the score but not the filename, so the caller
    passes the path it scored. Without it an annotation would point nowhere.
    """
    items = report.get("items")
    if items is None:
        return [{
            "file": report.get("file") or report.get("path") or scored_path or "input",
            "score": float(report.get("ai_likelihood", report.get("score", 0.0))),
            "band": report.get("band", ""),
        }]
    return [{"file": i.get("file", "input"), "score": float(i.get("score", 0.0)),
             "band": i.get("band", "")} for i in items]


def relative(path: str, workspace: str) -> str:
    """Make an absolute in-workspace path repo-relative, so annotations bind.

    A path already relative, or one outside the workspace, is returned as-is;
    relpath would otherwise walk it out of the repository with `../..`.
    """
    if not workspace or not os.path.isabs(path):
        return path
    try:
        resolved = os.path.relpath(path, workspace)
    except ValueError:  # different drive on Windows
        return path
    return path if resolved.startswith(os.pardir) else resolved


def annotations(rows: list[dict], gate: float, workspace: str) -> list[str]:
    return [
        f"::error file={relative(r['file'], workspace)},line=1::Writing score "
        f"{r['score']:g} is above the gate of {gate:g}"
        + (f" ({r['band']})" if r["band"] else "")
        + ". This describes the writing, not who wrote it."
        for r in rows if r["score"] > gate
    ]


def summary(rows: list[dict], gate: float, workspace: str) -> str:
    over = [r for r in rows if r["score"] > gate]
    worst = max((r["score"] for r in rows), default=0.0)
    verdict = "All clear." if not over else f"{len(over)} above the gate."
    lines = [
        "## Zero Slop", "",
        f"{len(rows)} document(s) scored against a gate of {gate:g}. "
        f"Highest score {worst:g}. {verdict}",
        "", "| File | Score | Band |", "|---|---:|---|",
    ]
    for row in sorted(rows, key=lambda r: -r["score"])[:SUMMARY_ROWS]:
        flag = "" if row["score"] <= gate else " &#9888;"
        lines.append(f"| `{relative(row['file'], workspace)}` | {row['score']:g}{flag} | {row['band']} |")
    if len(rows) > SUMMARY_ROWS:
        lines.append(f"| _and {len(rows) - SUMMARY_ROWS} more_ | | |")
    lines += ["", "_Lower is better. The score describes the writing, not who wrote it._"]
    return "\n".join(lines) + "\n"


def append(env_var: str, text: str) -> None:
    target = os.environ.get(env_var)
    if not target:
        return
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gate", type=float, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--annotate", default="true")
    parser.add_argument("--summary", default="true")
    parser.add_argument("--path", default="",
                        help="Path that was scored; names the file in a single-file report.")
    args = parser.parse_args(argv)

    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"::error::Zero Slop could not read its own report: {exc}", file=sys.stderr)
        return 1

    rows = normalise(report, args.path)
    workspace = os.environ.get("GITHUB_WORKSPACE", "")
    over = [r for r in rows if r["score"] > args.gate]
    worst = max((r["score"] for r in rows), default=0.0)

    if args.annotate == "true":
        for line in annotations(rows, args.gate, workspace):
            print(line)

    append("GITHUB_OUTPUT", "".join([
        f"passed={'true' if not over else 'false'}\n",
        f"max-score={worst:g}\n",
        f"documents={len(rows)}\n",
        f"report={json.dumps(report, separators=(',', ':'))}\n",
    ]))

    if args.summary == "true":
        append("GITHUB_STEP_SUMMARY", summary(rows, args.gate, workspace))

    print(f"Zero Slop: {len(rows)} document(s), highest {worst:g}, gate {args.gate:g} "
          f"— {'pass' if not over else 'fail'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
