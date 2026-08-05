#!/usr/bin/env python3
"""reward — turn a Zero Slop rewrite into the (hard, soft) score SkillOpt optimizes.

Microsoft's SkillOpt (github.com/microsoft/SkillOpt) treats a skill's SKILL.md as
trainable text: it runs the skill on a task set, scores each rollout, and keeps only
the edits to the instructions that strictly improve a held-out score. A SkillOpt
environment reports two numbers per rollout — a `hard` signal (0/1 correctness) and a
`soft` signal (a continuous [0,1] quality), both higher-is-better. Zero Slop already
ships every part of both, so this file just assembles them:

    hard  fidelity — every fact kept, nothing invented    (slopscore.fidelity)
    soft  a blend of, all from slopscore:
            de-slop gain   how much AI register the rewrite removed
            gate           did it clear the genre threshold
            rhythm         human sentence variance, not a uniform cadence
            length         still a rewrite, not a compression down to a stub

Keeping fidelity as its own `hard` channel is the whole trick. An optimizer cannot
buy a better `soft` score by dropping an inconvenient number or inventing a vivid
detail — that just sends `hard` to zero, and SkillOpt gates on both. Invention is
weighted as the catastrophe hard rule 1 says it is: a rewrite that *adds* a fact or a
feeling fails `hard` outright, while one that merely drops a token is penalised but
not erased, so the gradient toward "clean *and* faithful" stays smooth.

    python3 bench/skillopt/reward.py --baseline   # score the shipped skill's own
                                                  # benchmark rewrites (runs today,
                                                  # no network, no optimizer)

The optimizer itself needs an LLM to run rollouts and is a maintainer/CI job, never a
user runtime dependency — see this folder's README. The scoring here needs no network.
"""
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
ROOT = BENCH.parent
sys.path.insert(0, str(ROOT / "scripts"))

# The soft quality and the fidelity flags both come from slopscore.rewrite_score —
# the one rewrite objective shared with the runtime reranker (scripts/rerank.py), so
# what the optimizer is tuning toward is exactly what selection picks at run time.
WEIGHTS = ("deslop", "gate", "rhythm", "length")   # the soft components, for reporting


def components(original, rewrite, genre=None):
    """Every raw signal for one (draft, rewrite) pair."""
    import slopscore
    r = slopscore.rewrite_score(original, rewrite, genre)
    return {**r, "dropped": not r["preserved"]}


def hard(c):
    """Fidelity as SkillOpt's discrete signal. Invention is disqualifying; a merely
    dropped token is a heavy penalty, not a zero, so the optimizer still sees a path
    up from an imperfect rewrite toward a faithful one."""
    if c["invented"]:
        return 0.0
    return 1.0 if not c["dropped"] else 0.3


def score(original, rewrite, genre=None):
    """The (hard, soft) pair SkillOpt records for one rollout."""
    c = components(original, rewrite, genre)
    return {"hard": round(hard(c), 4), "soft": c["soft"]}


def score_batch(items):
    """Score a list of rollouts. Each item: {'id','original','rewrite','genre'?}.
    Returns SkillOpt-shaped result dicts: {'id','hard','soft'}."""
    out = []
    for it in items:
        s = score(it["original"], it["rewrite"], it.get("genre"))
        out.append({"id": it.get("id"), **s})
    return out


def summary(scored):
    n = len(scored) or 1
    return {"mean_hard": round(sum(r["hard"] for r in scored) / n, 4),
            "mean_soft": round(sum(r["soft"] for r in scored) / n, 4),
            "n": len(scored)}


def _baseline():
    """Score the shipped skill's own benchmark rewrites — a runnable sanity check.

    Pairs the 50 drafts in examples.json with the Zero Slop rewrites already in
    bench/outputs/, so the harness demonstrably runs on real data before anyone wires
    up the optimizer. These are the numbers a tuned SKILL.md has to beat on a
    held-out split.
    """
    ex = {e["id"]: e for e in json.loads((BENCH / "examples.json").read_text())}
    rewrites = {}
    for f in ("zeroslop12_h1.json", "zeroslop12_h2.json"):
        p = BENCH / "outputs" / f
        if p.exists():
            rewrites.update(json.loads(p.read_text()))

    items, comps = [], []
    for rid, rw in rewrites.items():
        if rid in ex:
            items.append({"id": rid, "original": ex[rid]["draft"],
                          "rewrite": rw, "genre": ex[rid].get("genre")})
            comps.append(components(ex[rid]["draft"], rw, ex[rid].get("genre")))
    scored = score_batch(items)
    s = summary(scored)

    dropped = sum(1 for c in comps if c["dropped"] and not c["invented"])
    invented = sum(1 for c in comps if c["invented"])
    clean = len(comps) - dropped - invented
    means = {k: round(sum(c[k] for c in comps) / len(comps), 3) for k in WEIGHTS}

    print(f"reward harness · {s['n']} rollouts from the shipped skill\n")
    print(f"  mean hard (fidelity)  {s['mean_hard']:.3f}   (1 clean · 0.3 dropped · 0 invented)")
    print(f"  mean soft (quality)   {s['mean_soft']:.3f}   (0–1, higher is better)")
    import slopscore
    print("  soft component means:")
    for k in WEIGHTS:
        print(f"    {k:<8} {means[k]:.3f}   (weight {slopscore.RW_WEIGHTS[k]})")
    print(f"  fidelity split        {clean} clean · {dropped} dropped a token · "
          f"{invented} invented")
    print("\nSkillOpt maximises both signals under a held-out validation gate.")
    return 0


def main():
    if "--baseline" in sys.argv:
        return _baseline()
    print(__doc__)
    print("run with --baseline to score the shipped skill's benchmark rewrites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
