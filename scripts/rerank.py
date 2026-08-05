#!/usr/bin/env python3
"""rerank — generate several rewrites, keep the best one, objectively.

A single rewrite is one sample from the model. Two or three, written with different
strategies (strip hard vs. keep the warmth, reorder vs. stay put), give the loop
something to choose between — and the choice should be made by the meter, not by the
same taste that wrote them. This ranks candidates for one draft and returns the
winner, using the shared rewrite objective in slopscore (`rewrite_score`), the same
one the SkillOpt reward tunes toward.

The order is not negotiable on fidelity. A candidate that invents a fact loses to any
candidate that does not, however much cleaner it reads, because inventing a detail is
the one thing hard rule 1 forbids. Among the faithful candidates, the best de-slop
quality wins.

    python3 scripts/rerank.py --original draft.md cand1.md cand2.md cand3.md
    python3 scripts/rerank.py --original draft.md --candidates cands.json   # {name: text}
    python3 scripts/rerank.py --original draft.md --genre linkedin *.md --out best.md

Prints a comparison table and marks the winner; writes the winning text to --out, or
to stdout with --emit. Offline, standard library only, like the rest of the scorer.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _tier(s):
    """0 clean · 1 dropped a fact · 2 invented a fact. Lower is better, always."""
    if s["invented"]:
        return 2
    return 0 if s["preserved"] else 1


def rank(original, candidates, genre=None):
    """candidates: {name: text}. Returns them scored and sorted, best first.

    Sort key: fidelity tier first (a fabrication can never win), then soft quality,
    then the tie-breaks the verify gate cares about — lower AI-likelihood, more
    burstiness, fewer high-weight tells.
    """
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
        out.append(f"  winner: {win['name']} — faithful and cleanest of {len(scored)}.")
    else:
        out.append(f"  winner: {win['name']} — but NO candidate was fully faithful "
                   f"({labels[_tier(win)]}). Regenerate or fix the fact before shipping.")
    return "\n".join(out)


def _read(argv, flag):
    return argv[argv.index(flag) + 1] if flag in argv else None


def main():
    argv = sys.argv[1:]
    original_path = _read(argv, "--original")
    if not original_path:
        print("usage: rerank.py --original draft.md cand1.md cand2.md ...")
        return 2
    original = Path(original_path).read_text()
    genre = _read(argv, "--genre")

    if "--candidates" in argv:
        candidates = json.loads(Path(_read(argv, "--candidates")).read_text())
    else:
        skip = {"--original", original_path, "--genre", genre, "--out",
                _read(argv, "--out"), "--emit"}
        files = [a for a in argv if a not in skip and not a.startswith("--")]
        candidates = {Path(f).name: Path(f).read_text() for f in files}
    if len(candidates) < 2:
        print("give at least two candidate rewrites to choose between")
        return 2

    scored = rank(original, candidates, genre)
    print(render(scored))
    win = scored[0]
    out = _read(argv, "--out")
    if out:
        Path(out).write_text(win["text"])
        print(f"\n  wrote {out}")
    elif "--emit" in argv:
        print("\n" + "=" * 60 + "\n" + win["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
