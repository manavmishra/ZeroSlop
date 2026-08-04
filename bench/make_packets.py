#!/usr/bin/env python3
"""Build blind judging packets: shuffle method labels per example (seed 42)."""
import json
import random
from pathlib import Path

E = Path(__file__).parent
METHODS = ["zeroslop", "petergyang", "blader", "deslop"]

examples = {e["id"]: e for e in json.loads((E / "examples.json").read_text())}
outputs = {}
for m in METHODS:
    outputs[m] = {}
    for half in ["h1", "h2"]:
        f = E / "outputs" / f"{m}_{half}.json"
        outputs[m].update(json.loads(f.read_text()))

missing = [(m, i) for m in METHODS for i in examples if i not in outputs[m]]
if missing:
    raise SystemExit(f"missing rewrites: {missing}")

rng = random.Random(42)
ids = sorted(examples)
key = {}  # example_id -> {label: method}
packets = []
for i in ids:
    labels = ["A", "B", "C", "D"]
    ms = METHODS[:]
    rng.shuffle(ms)
    key[i] = dict(zip(labels, ms))
    packets.append({
        "id": i,
        "genre": examples[i]["genre"],
        "brief": examples[i]["brief"],
        "facts": examples[i]["facts"],
        "original_draft": examples[i]["draft"],
        "variants": {lab: outputs[m][i] for lab, m in key[i].items()},
    })

(E / "judging").mkdir(exist_ok=True)
(E / "judging" / "key.json").write_text(json.dumps(key, indent=1))
for j in range(5):
    chunk = packets[j * 10:(j + 1) * 10]
    (E / "judging" / f"packet-{j+1}.json").write_text(
        json.dumps(chunk, indent=1, ensure_ascii=False))
print("packets written:", 5, "key:", len(key))
