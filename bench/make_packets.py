#!/usr/bin/env python3
"""Build blind judging packets: shuffle method labels per example (seed 42)."""
import json
import random
import sys
from pathlib import Path

E = Path(__file__).resolve().parent
sys.path.insert(0, str(E.parent / "scripts"))
from safeio import atomic_write_text  # noqa: E402
METHODS = ["zeroslop", "petergyang", "blader", "deslop"]

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
            or not isinstance(row.get("brief"), str) or not row["brief"].strip()
            or not isinstance(row.get("draft"), str) or not row["draft"].strip()
            or not isinstance(row.get("facts"), list)):
        raise SystemExit(
            f"{row['id']}: genre, brief, draft, and facts have invalid shapes"
        )
examples = {e["id"]: e for e in raw_examples}
outputs = {}
for m in METHODS:
    outputs[m] = {}
    for half in ["h1", "h2"]:
        f = E / "outputs" / f"{m}_{half}.json"
        part = json.loads(f.read_text())
        if not isinstance(part, dict):
            raise SystemExit(f"{f.name} must be an object keyed by example id")
        overlap = set(outputs[m]) & set(part)
        if overlap:
            raise SystemExit(f"{f.name} repeats ids: {sorted(overlap)}")
        outputs[m].update(part)

missing = [(m, i) for m in METHODS for i in examples if i not in outputs[m]]
extra = [(m, i) for m in METHODS for i in outputs[m] if i not in examples]
if missing or extra:
    raise SystemExit(f"rewrite id mismatch: missing={missing}, extra={extra}")
for method, rows in outputs.items():
    for item_id, value in rows.items():
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"{method}:{item_id} rewrite must be non-empty text")

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
atomic_write_text(E / "judging" / "key.json", json.dumps(key, indent=1) + "\n")
for j in range(5):
    chunk = packets[j * 10:(j + 1) * 10]
    atomic_write_text(
        E / "judging" / f"packet-{j+1}.json",
        json.dumps(chunk, indent=1, ensure_ascii=False) + "\n",
    )
print("packets written:", 5, "key:", len(key))
