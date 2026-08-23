# Benchmark harness

Everything needed to reproduce, contest, or extend the evaluation in
[EVALUATION.html](../EVALUATION.html).

- `examples.json` — the 50-draft corpus (25 LinkedIn, 8 blog, 5 newsletter,
  5 X/Twitter, 4 email, 3 research), each with the brief and ground-truth
  facts used for fidelity checking.
- `outputs/` — every method's rewrites, one file per method per half.
- `judging/` — blinded LLM-rating packets, the shuffle key, run-one scores
  (`scores-*.json`) and the replication scores (`rep2-scores-*.json`).
- `replication.py` — run-to-run tally, per-item agreement, Cohen's kappa,
  Wilson intervals and the exact Zero Slop–humanizer selection test. This is the
  script that moved the headline from 32/50 to
  a pooled 55/100.
- `aggregate.py`, `make_packets.py` — scorecard aggregation and packet
  construction (seeded shuffles, so packets rebuild identically).
- `objective-panel.json`, `judge-dimensions.json`, `replication.json` —
  computed results.
- `search-corpus/` — 18 anonymous, search-informed slop paraphrases across
  LinkedIn, X, email, blog, newsletter, and research, plus five pinned rewrite
  methods and an item-level public AIStoryHub checker cross-check.
- `aistoryhub-corpus/` — a version-and-hash-pinned coverage audit against the
  public AIStoryHub taxonomy. It reports coverage, never accuracy, and does not
  redistribute the source JSON.
- `beemo-corpus/` — a revision-pinned paired audit of raw model responses,
  expert human edits, and independent human answers. It fetches on demand,
  commits only aggregate results, and does not treat provenance as slop quality.
- `external-models/` — a pinned reproduction of The Slop Index mechanical
  benchmark on its 19,928 preserved generations. It is external model context,
  not a Zero Slop result.
- `performance.py`, `performance-results.json` — local scorer and learning-loop
  timings with the machine record, raw runs, medians, and CI ceilings.
- `quality-corpus/` — a method-hidden, source-grouped 72-item editorial-quality
  panel with two independent label files, unresolved disagreements, and split metrics.
- `feature-ablation/` — the reproducible v2.4.3-versus-v2.5.1 comparison, including
  exact production score-vector hashes and bounded local timing observations.
- `corpus-registry.json`, `validate_corpus_registry.py` — the admission decision for
  every proposed external corpus. Label semantics, provenance, access terms, and the
  claim a corpus may support are explicit; authorship labels never stand in for
  slop-quality labels.

## Reproducing

```bash
python3 bench/replication.py          # agreement and pooled statistics
python3 bench/aggregate.py            # per-method scorecard
python3 bench/search-corpus/evaluate.py --check
python3 bench/search-corpus/compare.py --check
python3 bench/aistoryhub-corpus/audit.py --fetch --check
python3 bench/beemo-corpus/audit.py --fetch --check
python3 bench/quality-corpus/build_manifest.py --check
python3 bench/quality-corpus/evaluate.py --manifest bench/quality-corpus/manifest.json --labels bench/quality-corpus/labels-rater-a.json --labels bench/quality-corpus/labels-rater-b.json --out bench/quality-corpus/results.json --check
python3 bench/feature-ablation/check.py
python3 bench/validate_corpus_registry.py
python3 bench/make_charts.py --check
```

Refresh the local performance observation separately with
`python3 bench/performance.py --write`; wall-clock results are intentionally not
treated as bit-for-bit reproducible across machines.

## How the judging worked

No human raters took part. The 50 examples were divided into five packets of ten. For
each item, the packet contained the writing brief, original draft, factual inventory,
and four rewrites labeled A through D. A seeded shuffle hid which method produced each
rewrite.

Each pass used five fresh LLM judge runs from the same model family, one per packet. A
judge scored every rewrite from 1 to 10 on five labeled dimensions: human-likeness,
voice, fidelity, writing craft, and platform fit. It also marked possible fabrication
and selected the best and worst rewrite. A second set of five LLM runs reviewed the
same packets with the same label mapping. That produced two ratings for each of the 50
items, or 100 item-level selections in total.

The repository preserves the packets, shuffle key, raw scores, and aggregation code.
It does not preserve the exact judge model and version, inference settings, or full
evaluation prompt. The ratings therefore cannot be reproduced exactly from the public
harness. Treat them as a small, model-specific experiment rather than human evidence or
a general ranking of the tools.

## Adding a method

Drop `outputs/<yourmethod>_h1.json` and `_h2.json` (id → rewritten text),
add the name to the `METHODS` list in `make_packets.py`, and rebuild the
packets. To compare results with the existing ratings, document the model,
version, settings, and complete evaluation prompt used for the new blinded pass.

## Known limits

The drafts are synthetic, the evaluation used LLMs rather than human raters, and the
same model family was used for generation and judging. The corpus has only 50 items.
Winner agreement between the two passes was 52%, with a Cohen's kappa of 0.12. The
exact judge configuration and prompt are missing, and competing outputs were recreated
from published prompts rather than produced by the live tools.
