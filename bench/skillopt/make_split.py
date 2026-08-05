#!/usr/bin/env python3
"""make_split — write the train/val/test split SkillOpt reads.

SkillOpt's `split_mode: split_dir` expects a folder of jsonl files, one row per
task. This derives them from the 50-draft benchmark in examples.json, so the
optimizer trains on the same drafts the skill is already measured against. The
split is deterministic (round-robin by genre-sorted index, no randomness) so a
re-run reproduces it exactly — the same contract as every other build here.

    python3 bench/skillopt/make_split.py            # write data/zeroslop_split/
"""
import json
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
OUT = BENCH.parent / "data" / "zeroslop_split"


def main():
    ex = json.loads((BENCH / "examples.json").read_text())
    items = [{"id": e["id"], "genre": e.get("genre"), "brief": e.get("brief", ""),
              "facts": e.get("facts", ""), "draft": e["draft"]}
             for e in sorted(ex, key=lambda e: e["id"])]
    # round-robin keeps every genre in every split; 0->test, 1->val, rest->train
    buckets = {"train": [], "val": [], "test": []}
    for i, it in enumerate(items):
        split = "test" if i % 6 == 0 else "val" if i % 6 == 1 else "train"
        buckets[split].append(it)

    OUT.mkdir(parents=True, exist_ok=True)
    for split, rows in buckets.items():
        path = OUT / f"{split}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"wrote {OUT.relative_to(BENCH.parent)}/  "
          + " · ".join(f"{k} {len(v)}" for k, v in buckets.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
