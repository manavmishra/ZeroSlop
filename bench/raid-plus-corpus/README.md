# RAID+ current-model audit

The retained receipt measures Zero Slop 2.12.12 across all 8,000 generations in
[RAID+](https://huggingface.co/datasets/markstanl/RAID-Plus). RAID+ extends the
peer-reviewed RAID benchmark with 2,000 outputs apiece from Gemini 3.1 Pro,
DeepSeek V3, Gemma 3 27B, and Llama 3.3 70B. The dataset is MIT-licensed and
intended for evaluation, not training.

```bash
python3 bench/raid-plus-corpus/audit.py --fetch --write
python3 bench/raid-plus-corpus/audit.py --fetch --check
python3 bench/raid-plus-corpus/audit.py --check
python3 bench/raid-plus-corpus/audit.py --check-historical
```

`source.json` pins the upstream commit, row count, model counts, and purpose.
The fetch path fails if that revision or schema moves. `results.json` contains
only aggregate scores and a SHA-256 fingerprint of the fetched rows; source
prompts and generations are never committed.

`--check-historical` validates the original receipt and source pin against fixed
commit `d065464b64d2ae46d72fde83f3c0b5da40bd149a`, including the measured scorer,
pattern, and shared-learning bytes. It performs no fetch or new measurement.
`--check` still rejects this older receipt when current runtime bytes differ.
The separate 2.12.16 deterministic release replay is not a new RAID+ replay;
none of these historical distributions is relabelled as version 2.12.16.

## What this can answer

The retained audit shows how strongly the measured 2.12.12 scorer reacts to unedited output from
four recent model families. It checks whether scoring behavior changes on newer
models and gives the release a repeatable regression test.
RAID+ labels machine provenance, not editorial quality, so these numbers are
not precision, recall, authorship accuracy, or proof that every high-scoring
passage is sloppy. There is no human comparison group in RAID+.

Abstracts use Zero Slop's formal-writing setting. Other domains use the general
setting. Empty or failed generations are counted in the source audit and
excluded from score summaries.
