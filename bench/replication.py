#!/usr/bin/env python3
"""Replication analysis: does 32/50 hold when fresh LLM judge runs re-score
the identical rewrites with the identical shuffled labels?

Reports run-to-run best-pick tallies, per-item agreement (how often the two
runs pick the same winner), Cohen's kappa on the winner choice, and a
Wilson confidence interval on the win rate.
"""
import json
import math
from pathlib import Path

E = Path(__file__).parent
key = json.load(open(E / "judging" / "key.json"))
METHODS = ["zeroslop", "blader", "petergyang", "deslop"]
DIMS = ["human", "voice", "fidelity", "craft", "platform"]


def load(prefix):
    picks, dims, fabs = {}, {m: {d: [] for d in DIMS} for m in METHODS}, {}
    n = 0
    for j in range(1, 6):
        f = E / "judging" / f"{prefix}scores-{j}.json"
        if not f.exists():
            return None, None, None, 0
        for it in json.loads(f.read_text()):
            picks[it["id"]] = key[it["id"]][it["best"]]
            n += 1
            for lab, sc in it["scores"].items():
                m = key[it["id"]][lab]
                for d in DIMS:
                    dims[m][d].append(sc[d])
                if sc.get("fabrication"):
                    fabs[m] = fabs.get(m, 0) + 1
    return picks, dims, fabs, n


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def kappa(a, b, cats):
    ids = [i for i in a if i in b]
    if not ids:
        return float("nan")
    po = sum(1 for i in ids if a[i] == b[i]) / len(ids)
    pe = sum((sum(1 for i in ids if a[i] == c) / len(ids)) *
             (sum(1 for i in ids if b[i] == c) / len(ids)) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def tally(picks):
    t = {m: 0 for m in METHODS}
    for v in picks.values():
        t[v] = t.get(v, 0) + 1
    return t


r1_picks, r1_dims, r1_fabs, n1 = load("")
r2_picks, r2_dims, r2_fabs, n2 = load("rep2-")

print("=" * 66)
print("REPLICATION: same 50 rewrites and labels, fresh LLM judge runs")
print("=" * 66)
t1 = tally(r1_picks)
print(f"\nRun 1 best-picks (n={n1}): {t1}")
if r2_picks is None:
    print("\nRun 2 incomplete — waiting on judges.")
    raise SystemExit(0)

t2 = tally(r2_picks)
print(f"Run 2 best-picks (n={n2}): {t2}")

print("\nZero-Slop win rate")
for label, t, n in [("run 1", t1, 50), ("run 2", t2, 50)]:
    k = t["zeroslop"]
    lo, hi = wilson(k, n)
    print(f"  {label}: {k}/{n} = {k/n:.0%}   95% CI [{lo:.0%}, {hi:.0%}]")
pooled_k = t1["zeroslop"] + t2["zeroslop"]
lo, hi = wilson(pooled_k, 100)
print(f"  pooled: {pooled_k}/100 = {pooled_k/100:.0%}   95% CI [{lo:.0%}, {hi:.0%}]")

agree = sum(1 for i in r1_picks if r1_picks[i] == r2_picks.get(i))
print(f"\nPer-item winner agreement: {agree}/50 = {agree/50:.0%}")
print(f"Cohen's kappa (winner choice): {kappa(r1_picks, r2_picks, METHODS):.3f}")

print("\nComposite by run")
print(f"{'method':14s} {'run1':>6s} {'run2':>6s} {'delta':>7s}")
for m in METHODS:
    c1 = sum(sum(r1_dims[m][d]) for d in DIMS) / (5 * len(r1_dims[m]["human"]))
    c2 = sum(sum(r2_dims[m][d]) for d in DIMS) / (5 * len(r2_dims[m]["human"]))
    print(f"{m:14s} {c1:6.2f} {c2:6.2f} {c2-c1:+7.2f}")

print(f"\nFabrication flags — run 1: {r1_fabs or 'none'}   run 2: {r2_fabs or 'none'}")
json.dump({"run1": t1, "run2": t2, "agreement": agree / 50,
           "kappa": kappa(r1_picks, r2_picks, METHODS),
           "pooled_ci": wilson(pooled_k, 100)},
          open(E / "replication.json", "w"), indent=1)
