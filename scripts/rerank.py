#!/usr/bin/env python3
"""rerank — generate several rewrites, keep the best one, objectively.

A single rewrite is one sample from the model. Two or three, written with different
strategies (strip hard vs. keep the warmth, reorder vs. stay put), give the loop
something to choose between — and the choice should be made by the meter, not by the
same taste that wrote them. This ranks candidates for one draft and returns the
winner, using the shared rewrite objective in slopscore (`rewrite_score`).

The order is not negotiable on fidelity. A version that invents a fact loses to any
version that does not, however much cleaner it reads, because inventing a detail is
the one thing hard rule 1 forbids. Of the versions that preserve the source, the
cleanest one wins.

    python3 scripts/rerank.py --original draft.md cand1.md cand2.md cand3.md
    python3 scripts/rerank.py --original draft.md --candidates cands.json   # {name: text}
    python3 scripts/rerank.py --original draft.md --genre linkedin *.md --out best.md

Prints a comparison table and marks the winner; writes the winning text to --out, or
to stdout with --emit. Offline, standard library only, like the rest of the scorer.
"""
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from safeio import atomic_write_text


def _tier(s):
    """0 clean · 1 dropped a fact · 2 invented a fact. Lower is better, always."""
    if s["invented"]:
        return 2
    return 0 if s["preserved"] else 1


def rank(original, candidates, genre=None):
    """candidates: {name: text}. Returns them scored and sorted, best first.

    Sort key: fidelity tier first (a fabrication can never win), then soft quality,
    then the tie-breaks the verify gate cares about — lower surface score, more
    burstiness, fewer high-weight tells.
    """
    if not isinstance(original, str):
        raise ValueError("original must be text")
    if not isinstance(candidates, dict) or not candidates:
        raise ValueError("candidates must be a non-empty object")
    for name, text in candidates.items():
        if (not isinstance(name, str) or not name.strip()
                or not isinstance(text, str) or not text.strip()):
            raise ValueError("candidate names and values must be non-empty names and text")
    import slopscore
    data = slopscore.load_patterns()
    scored = []
    for name, text in candidates.items():
        s = slopscore.rewrite_score(original, text, genre, data)
        s["name"], s["text"] = name, text
        scored.append(s)
    scored.sort(key=lambda s: (_tier(s), -s["soft"], s["after_ai"],
                               -s["burstiness"], s["high_tells"]))
    return scored


def render(scored):
    out = ["", "  candidate            soft   AI    burst  htells  fidelity",
           "  " + "-" * 56]
    labels = {0: "clean ✓", 1: "dropped a fact", 2: "INVENTED ✗"}
    for i, s in enumerate(scored):
        mark = "→" if i == 0 else " "
        out.append(f"  {mark} {s['name'][:18]:<18} {s['soft']:.3f}  {s['after_ai']:>4}  "
                   f"{s['burstiness']:.2f}   {s['high_tells']:>3}    {labels[_tier(s)]}")
    win = scored[0]
    out.append("")
    if _tier(win) == 0:
        out.append(
            f"  winner: {win['name']} — cleanest of {len(scored)} versions "
            "that preserve the source."
        )
    else:
        out.append(
            f"  winner: {win['name']} — but every version changed or dropped "
            f"source material ({labels[_tier(win)]}). Regenerate or fix the fact "
            "before shipping."
        )
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--original", required=True, metavar="FILE")
    ap.add_argument("--candidates", metavar="JSON_FILE")
    ap.add_argument("--genre")
    ap.add_argument("--out", metavar="FILE")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("files", nargs="*")
    args = ap.parse_args(argv)
    try:
        original = Path(args.original).read_text()
    except (OSError, UnicodeDecodeError) as exc:
        ap.error(f"cannot read original: {exc}")

    if args.candidates:
        if args.files:
            ap.error("use either --candidates JSON_FILE or candidate files, not both")
        try:
            candidates = json.loads(Path(args.candidates).read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            ap.error(f"cannot read candidates: {exc}")
    else:
        candidates = {}
        for file_name in args.files:
            path = Path(file_name)
            if path.name in candidates:
                ap.error(f"candidate basenames must be unique: {path.name}")
            try:
                candidates[path.name] = path.read_text()
            except (OSError, UnicodeDecodeError) as exc:
                ap.error(f"cannot read candidate {path}: {exc}")
    if len(candidates) < 2:
        ap.error("give at least two candidate rewrites to choose between")

    try:
        scored = rank(original, candidates, args.genre)
    except ValueError as exc:
        ap.error(str(exc))
    print(render(scored))
    win = scored[0]
    if args.out:
        output = Path(args.out).resolve()
        protected = {Path(args.original).resolve()}
        if args.candidates:
            protected.add(Path(args.candidates).resolve())
        protected.update(Path(path).resolve() for path in args.files)
        if output in protected:
            ap.error("--out must not overwrite the original or a candidate input")
        try:
            atomic_write_text(output, win["text"])
        except OSError as exc:
            ap.error(f"cannot write winner: {exc}")
        print(f"\n  wrote {args.out}")
    elif args.emit:
        print("\n" + "=" * 60 + "\n" + win["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
