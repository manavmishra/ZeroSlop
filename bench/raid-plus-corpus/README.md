# RAID+ current-model audit

This audit runs the current Zero Slop scorer across all 8,000 generations in
[RAID+](https://huggingface.co/datasets/markstanl/RAID-Plus). RAID+ extends the
peer-reviewed RAID benchmark with 2,000 outputs apiece from Gemini 3.1 Pro,
DeepSeek V3, Gemma 3 27B, and Llama 3.3 70B. The dataset is MIT-licensed and
intended for evaluation, not training.

```bash
python3 bench/raid-plus-corpus/audit.py --fetch --write
python3 bench/raid-plus-corpus/audit.py --fetch --check
python3 bench/raid-plus-corpus/audit.py --check
```

`source.json` pins the upstream commit, row count, model counts, and purpose.
The fetch path fails if that revision or schema moves. `results.json` contains
only aggregate scores and a SHA-256 fingerprint of the fetched rows; source
prompts and generations are never committed.

## What this can answer

The audit shows how strongly the current scorer reacts to unedited output from
four recent model families. It checks whether scoring behavior changes on newer
models and gives the release a repeatable regression test.
RAID+ labels machine provenance, not editorial quality, so these numbers are
not precision, recall, authorship accuracy, or proof that every high-scoring
passage is sloppy. There is no human comparison group in RAID+.

Abstracts use Zero Slop's formal-writing setting. Other domains use the general
setting. Empty or failed generations are counted in the source audit and
excluded from score summaries.
