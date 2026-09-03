# Benchmark harness

This directory contains everything needed to reproduce, contest, or extend the
historical evaluation in [EVALUATION.html](../EVALUATION.html), along with the
current corpus checks.

- `examples.json` — the 50-draft corpus (25 LinkedIn, 8 blog, 5 newsletter,
  5 X/Twitter, 4 email, 3 research), each with the brief and ground-truth
  facts used for fidelity checking.
- `outputs/` — every method's rewrites, one file per method per half.
- `judging/` — method-hidden LLM-rating packets, the shuffle key, run-one scores
  (`scores-*.json`) and the replication scores (`rep2-scores-*.json`).
- `replication.py` — run-to-run tally, per-item agreement, Cohen's kappa,
  Wilson intervals and the exact Zero Slop–humanizer selection test. This is the
  script that moved the headline from 32/50 to
  a pooled 55/100.
- `aggregate.py`, `make_packets.py` — scorecard aggregation and packet
  construction (seeded shuffles, so packets rebuild identically).
- `objective-panel.json`, `judge-dimensions.json`, `replication.json` —
  computed results.
- `antithesis/` — 58 labelled adjacent-sentence pairs, 30 antithesis and 28
  ordinary, for the reading pass's antithesis detector. The negatives are
  adversarial for that detector: negation that is not a figure, anaphora,
  repeated subjects, shared vocabulary, and parallel technical prose. Two
  positive shapes are documented as out of reach and count against recall
  rather than being excused. Maintainer labels on constructed pairs.
- `search-corpus/` — 18 anonymous, search-informed slop paraphrases across
  LinkedIn, X, email, blog, newsletter, and research, plus five pinned rewrite
  methods and an item-level public AIStoryHub checker cross-check.
- `fresh-replay/` — fresh GPT-5.4 rewrites of those 18 drafts from Zero Slop,
  avoid-ai-writing, no-ai-slop, and humanizer. Every run used the same model,
  reasoning level, batch size, corpus, and isolated harness; hashes bind the
  instructions, prompts, and outputs.
- `incumbent-audit/` — the avoid-ai-writing detector at its pinned commit applied
  to Zero Slop's frozen 38-item consensus panel. It preserves the published gate,
  a development-selected gate, and the held-out result.
- `incumbent-blind-replay/` — a fresh method-hidden two-way replay of Zero Slop
  and the pinned incumbent. It keeps editing and review settings equal, reshuffles
  A/B positions between two review passes, and binds every artifact by hash.
- `aistoryhub-corpus/` — a version-and-hash-pinned coverage audit against the
  public AIStoryHub taxonomy. It reports coverage, never accuracy, and does not
  redistribute the source JSON.
- `beemo-corpus/` — a revision-pinned paired audit of raw model responses,
  expert human edits, and independent human answers. It fetches on demand,
  commits only aggregate results, and does not treat provenance as slop quality.
- `raid-plus-corpus/` — all 8,000 rows from the MIT-licensed RAID+ extension,
  with 7,627 non-empty generations from four current model families scored at a
  pinned revision. It is a current-distribution cross-check, not slop accuracy.
- `external-models/` — a pinned reproduction of The Slop Index mechanical
  benchmark on its 19,928 preserved generations. It is external model context,
  not a Zero Slop result.
- `performance.py`, `performance-results.json` — local scorer and learning-loop
  timings with the machine record, raw runs, medians, and CI ceilings.
- `version_compare.py`, `version-comparison.json` — the 12-run interleaved
  v2.7.7/v2.7.8 timing vectors, exact scorer hashes, frozen score parity, new
  adversarial cases, and structured-document protections.
- `quality-corpus/` — a method-hidden, source-grouped 72-item editorial-quality
  panel with two independent label files, unresolved disagreements, and split metrics.
- `feature-ablation/` — the reproducible contextual research comparison, including
  exact score-vector hashes and the frozen quality-panel result.
- `corpus-registry.json`, `validate_corpus_registry.py` — the admission decision for
  every proposed external corpus. Label semantics, provenance, access terms, and the
  claim a corpus may support are explicit; authorship labels never stand in for
  slop-quality labels.
- `internal-corpus/` — a hash-pinned replay of Manav's nine-example private Google
  Doc. The source stays in `~/.zero-slop/evals/`; only aggregate findings are
  committed. It catches drift and missed cases but does not measure accuracy.
- `competitor-capabilities.json` — a feature-presence audit at pinned commits for
  Zero Slop, avoid-ai-writing, humanizer, no-ai-slop, and JCarterJohnson's
  unslop-text. It records what each repository documents; it does not measure which
  editor writes better.

## Reproducing

```bash
python3 bench/replication.py          # agreement and pooled statistics
python3 bench/aggregate.py            # per-method scorecard
python3 bench/search-corpus/evaluate.py --check
python3 bench/search-corpus/compare.py --check
python3 bench/fresh-replay/evaluate.py --avoid-root /path/to/pinned/avoid-ai-writing
python3 bench/incumbent-audit/evaluate.py --avoid-root /path/to/pinned/avoid-ai-writing
python3 bench/incumbent-blind-replay/evaluate.py --avoid-root /path/to/pinned/avoid-ai-writing
python3 bench/aistoryhub-corpus/audit.py --fetch --check
python3 bench/beemo-corpus/audit.py --fetch --check
python3 bench/raid-plus-corpus/audit.py --fetch --check
python3 bench/quality-corpus/build_manifest.py --check
python3 bench/quality-corpus/evaluate.py --manifest bench/quality-corpus/manifest.json --labels bench/quality-corpus/labels-rater-a.json --labels bench/quality-corpus/labels-rater-b.json --out bench/quality-corpus/results.json --check
python3 bench/antithesis/evaluate.py --check
python3 bench/internal-corpus/evaluate.py --check
python3 bench/feature-ablation/check.py
python3 bench/validate_corpus_registry.py
python3 bench/make_charts.py --check
```

Refresh the local performance observation separately with
`python3 bench/performance.py --write`; wall-clock results are intentionally not
treated as bit-for-bit reproducible across machines.

## Current incumbent comparison

The v2.6.0 two-way replay used GPT-5.4, high reasoning, batches of three, and the
same 18 drafts for both skills. Method names were removed before two editorial
review passes, and A/B positions were reshuffled. The reviewer favored Zero Slop
on 13 drafts and avoid-ai-writing on 3; 2 were unresolved. The passes agreed on
16 of 18 winners. Zero Slop's source check passed 18 of its rewrites and 16 of the
incumbent's. This is a small LLM-reviewed regression study, not human field
accuracy or a universal ranking. The raw artifacts live in
[`incumbent-blind-replay/`](incumbent-blind-replay/).

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

The repository preserves the packets, shuffle key, raw scores, and aggregation code,
but it does not preserve the exact judge model and version, inference settings, or full
evaluation prompt. The ratings therefore cannot be reproduced exactly from the public
harness. Treat them as a small, model-specific experiment rather than human evidence or
a general ranking of the tools.

## Adding a method

Drop `outputs/<yourmethod>_h1.json` and `_h2.json` (id → rewritten text),
add the name to the `METHODS` list in `make_packets.py`, and rebuild the
packets. To compare results with the existing ratings, document the model,
version, settings, and complete evaluation prompt used for the new method-hidden pass.

## Known limits

The drafts are synthetic, the evaluation used LLMs rather than human raters, and the
same model family was used for generation and judging. The corpus has only 50 items.
Winner agreement between the two passes was 52%, with a Cohen's kappa of 0.12. The
exact judge configuration and prompt are missing, and competing outputs were recreated
from published prompts rather than produced by the live tools.
