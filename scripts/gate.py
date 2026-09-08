#!/usr/bin/env python3
"""Score many files at once and fail above a threshold.

slopscore's report mode takes a single file. Hook runners and shell globs hand
over a whole list, so this wraps the scorer with a multi-file gate:

    zero-slop-gate --gate 25 a.md b.md docs/c.md

Exit status is 1 when any file scores above the gate, 0 otherwise, which is the
contract pre-commit and CI expect. Nothing here re-implements scoring; it calls
the same score_text the skill, the wheel, and the hosted Worker use.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:  # installed wheel
    from zero_slop.scripts import slopscore
except ImportError:  # running from a source checkout
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import slopscore  # type: ignore


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--gate", type=float, default=25.0,
                        help="maximum allowed writing score (default: 25)")
    parser.add_argument("--formal", action="store_true",
                        help="score with the rules for professional writing")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the files above the gate")
    args = parser.parse_args(argv)

    if not args.files:
        return 0

    data = slopscore.load_patterns()
    failures: list[tuple[Path, float]] = []
    widest = max((len(str(f)) for f in args.files), default=0)

    for path in args.files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"{path}: cannot read ({exc})", file=sys.stderr)
            return 1
        if not text.strip():
            continue
        kwargs = {"formal": True} if args.formal else {}
        try:
            score = float(slopscore.score_text(text, data, **kwargs)["ai_likelihood"])
        except TypeError:  # older scorer without a formal keyword
            score = float(slopscore.score_text(text, data)["ai_likelihood"])
        over = score > args.gate
        if over:
            failures.append((path, score))
        if not args.quiet or over:
            mark = "  ABOVE GATE" if over else ""
            print(f"{str(path):<{widest}}  {score:6.1f}{mark}")

    if failures:
        print(f"\n{len(failures)} file(s) above the gate of {args.gate:g}. "
              f"Lower is better; the score describes the writing, not who wrote it.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
