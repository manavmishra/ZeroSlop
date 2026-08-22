#!/usr/bin/env python3
"""Aggregate objective scores + judge scores into the scorecard tables."""
import json
import statistics as st
import sys
from pathlib import Path

E = Path(__file__).parent
ROOT = E.parent
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402

METHODS = ["zeroslop", "petergyang", "blader", "deslop"]
DIMS = ["human", "voice", "fidelity", "craft", "platform"]

examples = {e["id"]: e for e in json.loads((E / "examples.json").read_text())}
data = slopscore.load_patterns()

# --- objective ---
outputs = {m: {} for m in METHODS}
for m in METHODS:
    for half in ["h1", "h2"]:
        outputs[m].update(json.loads((E / "outputs" / f"{m}_{half}.json").read_text()))

obj = {m: {} for m in METHODS}
orig_scores = {}
for i, e in examples.items():
    orig_scores[i] = slopscore.score_text(e["draft"], data)["ai_likelihood"]
    for m in METHODS:
        r = slopscore.score_text(outputs[m][i], data)
        obj[m][i] = {"ai": r["ai_likelihood"], "burst": r["burstiness"],
                     "words": r["n_words"]}

# --- judges ---
key = json.loads((E / "judging" / "key.json").read_text())
judge = {m: {d: [] for d in DIMS} for m in METHODS}
best = {m: 0 for m in METHODS}
worst = {m: 0 for m in METHODS}
fab = {m: 0 for m in METHODS}
per_genre = {}
n_judged = 0
for j in range(1, 6):
    f = E / "judging" / f"scores-{j}.json"
    if not f.exists():
        continue
    for item in json.loads(f.read_text()):
        i = item["id"]
        n_judged += 1
        g = examples[i]["genre"]
        for lab, sc in item["scores"].items():
            m = key[i][lab]
            for d in DIMS:
                judge[m][d].append(sc[d])
            per_genre.setdefault(g, {}).setdefault(m, []).append(
                sum(sc[d] for d in DIMS) / len(DIMS))
            if sc.get("fabrication"):
                fab[m] += 1
        best[key[i][item["best"]]] += 1
        worst[key[i][item["worst"]]] += 1

# --- report ---
rows = {}
for m in METHODS:
    ai = [obj[m][i]["ai"] for i in examples]
    br = [obj[m][i]["burst"] for i in examples if obj[m][i]["words"] > 60]
    jm = {d: (st.mean(judge[m][d]) if judge[m][d] else None) for d in DIMS}
    javg = st.mean([v for v in jm.values() if v is not None]) if any(
        v is not None for v in jm.values()) else None
    rows[m] = {
        "obj_ai_mean": round(st.mean(ai), 1),
        "obj_ai_median": round(st.median(ai), 1),
        "pct_clean_le25": round(100 * sum(1 for v in ai if v <= 25) / len(ai)),
        "burstiness_mean": round(st.mean(br), 3) if br else None,
        **{f"judge_{d}": (round(jm[d], 2) if jm[d] is not None else None)
           for d in DIMS},
        "judge_avg": round(javg, 2) if javg is not None else None,
        "best_picks": best[m], "worst_picks": worst[m],
        "fabrication_flags": fab[m],
    }

genre_tbl = {g: {m: round(st.mean(v), 2) for m, v in ms.items()}
             for g, ms in per_genre.items()}

out = {"orig_ai_mean": round(st.mean(orig_scores.values()), 1),
       "n_examples": len(examples), "n_judged_items": n_judged,
       "methods": rows, "per_genre_judge_avg": genre_tbl}
(E / "scorecard.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
