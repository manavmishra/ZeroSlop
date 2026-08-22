#!/usr/bin/env python3
"""Aggregate objective scores + judge scores into the scorecard tables."""
import json
import statistics as st
import sys
from pathlib import Path

E = Path(__file__).resolve().parent
ROOT = E.parent
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402
from safeio import atomic_write_text  # noqa: E402

METHODS = ["zeroslop", "petergyang", "blader", "deslop"]
DIMS = ["human", "voice", "fidelity", "craft", "platform"]

raw_examples = json.loads((E / "examples.json").read_text())
if not isinstance(raw_examples, list) or not raw_examples:
    raise SystemExit("examples.json must be a non-empty list")
if any(not isinstance(row, dict) or not isinstance(row.get("id"), str)
       for row in raw_examples):
    raise SystemExit("every example must be an object with a string id")
if len({row["id"] for row in raw_examples}) != len(raw_examples):
    raise SystemExit("examples.json contains duplicate ids")
for row in raw_examples:
    if (not isinstance(row.get("genre"), str) or not row["genre"].strip()
            or not isinstance(row.get("draft"), str) or not row["draft"].strip()):
        raise SystemExit(f"{row['id']}: genre and draft must be non-empty text")
examples = {e["id"]: e for e in raw_examples}
data = slopscore.load_patterns()

# --- objective ---
outputs = {m: {} for m in METHODS}
for m in METHODS:
    for half in ["h1", "h2"]:
        path = E / "outputs" / f"{m}_{half}.json"
        part = json.loads(path.read_text())
        if not isinstance(part, dict):
            raise SystemExit(f"{path.name} must be an object keyed by example id")
        overlap = set(outputs[m]) & set(part)
        if overlap:
            raise SystemExit(f"{path.name} repeats ids: {sorted(overlap)}")
        outputs[m].update(part)
    if set(outputs[m]) != set(examples):
        raise SystemExit(f"{m} output ids do not match examples.json")
    if any(not isinstance(value, str) or not value.strip()
           for value in outputs[m].values()):
        raise SystemExit(f"{m} contains an empty or non-text rewrite")

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
if not isinstance(key, dict) or set(key) != set(examples):
    raise SystemExit("judging/key.json ids do not match examples.json")
for item_id, mapping in key.items():
    if (not isinstance(mapping, dict) or set(mapping) != {"A", "B", "C", "D"}
            or set(mapping.values()) != set(METHODS)):
        raise SystemExit(f"invalid blind-label mapping for {item_id}")
judge = {m: {d: [] for d in DIMS} for m in METHODS}
best = {m: 0 for m in METHODS}
worst = {m: 0 for m in METHODS}
fab = {m: 0 for m in METHODS}
per_genre = {}
n_judged = 0
judged_ids = set()
for j in range(1, 6):
    f = E / "judging" / f"scores-{j}.json"
    if not f.exists():
        continue
    items = json.loads(f.read_text())
    if not isinstance(items, list):
        raise SystemExit(f"{f.name} must contain a list")
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise SystemExit(f"{f.name} contains a malformed judged item")
        i = item["id"]
        if i not in examples or i in judged_ids:
            raise SystemExit(f"{f.name} contains an unknown or duplicate id: {i}")
        judged_ids.add(i)
        scores = item.get("scores")
        labels = set(key[i])
        if not isinstance(scores, dict) or set(scores) != labels:
            raise SystemExit(f"{f.name}:{i} scores do not match its blind labels")
        if item.get("best") not in labels or item.get("worst") not in labels:
            raise SystemExit(f"{f.name}:{i} best/worst label is invalid")
        if item["best"] == item["worst"]:
            raise SystemExit(f"{f.name}:{i} best and worst cannot be the same")
        for label, values in scores.items():
            if (not isinstance(values, dict)
                    or any(not isinstance(values.get(dim), (int, float))
                           or isinstance(values.get(dim), bool)
                           or not 1 <= values[dim] <= 10 for dim in DIMS)
                    or not isinstance(values.get("fabrication", False), bool)):
                raise SystemExit(f"{f.name}:{i}:{label} has invalid judge scores")
        n_judged += 1
        g = examples[i]["genre"]
        for lab, sc in scores.items():
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
atomic_write_text(E / "scorecard.json", json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))
