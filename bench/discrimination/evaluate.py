#!/usr/bin/env python3
"""Discrimination test: does the meter separate known-slop from known-human?

The 50-draft benchmark measures how well competing *rewriters* do. This asks a
prior question about the *detector*: given text a reader would confidently label
either way, does the score agree? A gate is only useful if it does.

    python3 bench/discrimination/evaluate.py
"""
import json, sys, statistics as st
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import slopscore

GATE = 25.0
data = slopscore.load_patterns()
rows = json.loads((Path(__file__).parent / "corpus.json").read_text())

for r in rows:
    genre = "social" if r["genre"] in ("linkedin", "social", "reddit") else "general"
    s = slopscore.score_text(r["text"], data, formal=False)
    r["score"] = s["ai_likelihood"]
    r["tells"] = len(s["hits"])
    r["pred"] = "slop" if s["ai_likelihood"] > GATE else "human"

slop = [r["score"] for r in rows if r["label"] == "slop"]
hum  = [r["score"] for r in rows if r["label"] == "human"]

print(f"{'id':22s} {'genre':10s} {'label':6s} {'score':>7s} {'tells':>6s}  verdict")
for r in sorted(rows, key=lambda r: -r["score"]):
    ok = "ok" if r["pred"] == r["label"] else "MISCLASSIFIED"
    print(f"{r['id']:22s} {r['genre']:10s} {r['label']:6s} {r['score']:7.1f} "
          f"{r['tells']:6d}  {ok}")

correct = sum(1 for r in rows if r["pred"] == r["label"])
# AUC by rank: probability a random slop scores above a random human
pairs = [(a > b) + 0.5 * (a == b) for a in slop for b in hum]
auc = sum(pairs) / len(pairs)
print(f"\n  slop   n={len(slop):2d}  mean {st.mean(slop):5.1f}  range {min(slop):.1f}-{max(slop):.1f}")
print(f"  human  n={len(hum):2d}  mean {st.mean(hum):5.1f}  range {min(hum):.1f}-{max(hum):.1f}")
print(f"  separation: {st.mean(slop) - st.mean(hum):.1f} points")
print(f"  AUC: {auc:.3f}   accuracy at gate {GATE:g}: {correct}/{len(rows)}")
overlap = max(hum) >= min(slop)
print(f"  classes overlap: {'YES — ' + f'worst human {max(hum):.1f} >= best slop {min(slop):.1f}' if overlap else 'no, cleanly separated'}")
sys.exit(0 if correct == len(rows) else 1)
