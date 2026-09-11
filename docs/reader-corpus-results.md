# Zero Slop 2.12.0 candidate: corpus verification

Run date: September 10, 2026 Pacific / September 11 UTC. Local candidate based on
`0d866036b210b90e23fa9f7b4146316cf40c255e`. Not a published release.

## What the results establish

The scorer reproduces the small regression panels and the current-model RAID+
audit. It does **not** establish market-leading accuracy. On the more difficult
quality-labelled panel, four of nine consensus-clean items were flagged and two
of 29 consensus-sloppy items were missed. Thirty-four of 72 items had no agreed
binary label. Those limitations matter more than a perfect score on obvious
examples.

These are fresh scoring runs over existing texts and saved labels, not newly
generated rewrites, new human judgements, or new simulated-reader sessions. The
seven pinned scoring code/data files are unchanged from 2.11.6; the new optional
reader workflow cannot be credited with improving these scores.

## Detection and regression panels

| Corpus | Size | Observed result | What it measures |
| --- | ---: | --- | --- |
| Curated human controls | 12 texts | 12/12 false-positive regression checks passed | A small clean-text regression floor; a separate six-sample shape check retains one known lyric boundary |
| Constructed discrimination | 12 examples: six slop, six clean | 12/12 correctly separated; AUC 1.00 | Obvious authored exemplars, not sampled population accuracy |
| Cross-genre obvious slop | 18 paraphrases, six genres | 18/18 caught | Sensitivity on selected positive examples; no clean control group |
| Antithesis pairs | 75: 34 positive, 41 ordinary | 31 true positives, three misses, zero false positives, 41 true negatives | 91.2% recall; 100% precision and specificity on maintainer-labelled examples |
| Blind quality panel | 72 variants of 12 source drafts; 38 agreed binary labels | 32/38 correct: 84.2%; four false positives, two misses | Agreement with two saved LLM editorial labels, not independent human accuracy |
| Quality panel, held-out source split | 21 agreed labels | 20/21 correct: 95.2%; one miss, zero false positives | Only three clean controls; too small to establish strong specificity |

Do not sum these sample counts into an independent evaluation population. Panels
reuse source material and labels, and variants of one draft are correlated.

### Where the quality panel fails

Across all 38 agreed labels, precision is 87.1%, recall 93.1%, specificity 55.6%,
balanced accuracy 74.3%, and AUC 0.8142. The four false positives are all in the
development split; the two misses are split between development and test.

The evaluator's item-level Wilson interval is 69.6–92.6% for overall accuracy
and 77.3–99.2% for held-out accuracy. These intervals do not correct for clustering
within the 12 source drafts. Both labels are LLM judgements; disagreements and
borderline calls remain unresolved rather than being forced into a clean/sloppy
answer.

The antithesis misses are `anti-pos-27`, `anti-pos-28`, and `anti-pos-29`. They
remain in the recall denominator. Recognising semantic opposition is not the
same task as matching a lexical pattern.

### Cross-genre coverage

All three examples in each genre were caught. Mean surface scores, where lower
means fewer metered surface tells:

| Blog | Email | LinkedIn | Newsletter | Research | X |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 99.8 | 79.7 | 61.7 | 46.5 | 96.8 | 73.3 |

These means describe the examples, not relative accuracy between genres.

## External corpora: provenance is not slop quality

### RAID+: fresh fetch and rescore passed

Pinned revision `317600a0c8dd…`; 7,627 nonempty generations of 8,000 records.
The freshly fetched dataset reproduced the saved aggregate result. At the
generic surface gate of 25:

| Generator | Nonempty texts | Mean score | At or above gate |
| --- | ---: | ---: | ---: |
| DeepSeek V3 | 1,995 | 14.5 | 202 (10.1%) |
| Gemini 3.1 Pro | 1,998 | 17.0 | 363 (18.2%) |
| Gemma 3 27B | 1,634 | 21.6 | 497 (30.4%) |
| Llama 3.3 70B | 2,000 | 25.5 | 834 (41.7%) |

These are known model outputs, **not known bad writing**. A below-gate result is
not automatically a missed slop example. No authorship-detection accuracy follows
from these figures.

### Beemo: fresh measurement succeeded; saved-result check failed

Pinned revision `9c014107fe9b85c4c784c1ce3a43b0b7b0a6d162`; 2,187 paired
records, each containing raw model output, an expert edit, and an independent
human answer. The content hash matches the saved dataset exactly:
`2ae7fa4f5f54630887b1019591fbc1084a1ec9257010953a9041e7366a1530fd`.

| Text group | Fresh mean score | At or above 25 |
| --- | ---: | ---: |
| Raw model output | 30.3 | 846/2,187 (38.7%) |
| Expert human edit | 25.3 | 600/2,187 (27.4%) |
| Independent human answer | 19.9 | 348/2,187 (15.9%) |

Expert edits lower the score in 1,143/2,187 pairs (52.3%), leave it unchanged in
348, and raise it in 696. Mean reduction is 5.0 points; median reduction is 0.6.

The committed Beemo result dates from the 2.5.8 release and says raw mean 30.2,
841 raw texts above gate, and 1,141 lowered pairs. The strict fresh comparison
correctly failed. A second diagnostic fetch reproduced the source hash and
identified differences only in score aggregates and paired-edit aggregates.
The old result has not been overwritten or silently relabelled as 2.12.0.
No private learned-rule file was present in this environment.

Beemo's labels describe provenance and editing history, not slop, factual
correctness, or preference. The 348 human answers above gate must not be called
348 false positives without quality labels. Field-specific dataset terms apply;
no Beemo source text is included in this report.

## Saved rewrite comparison

Freshly rescored existing outputs on the same 18-source panel:

| Method | Mean surface score | Surface/shape gate plus tracked-fact pass | Word change |
| --- | ---: | ---: | ---: |
| Zero Slop | 16.4 | 18/18 | −26.4% |
| no-ai-slop | 29.1 | 12/18 | −28.0% |
| humanizer | 25.3 | 13/18 | −25.7% |
| de-slop | 52.3 | 6/18 | −18.5% |
| stop-slop | 25.7 | 13/18 | −34.4% |

The original rewrites are frozen outputs from a shared host-model experiment.
They were not regenerated with 2.12.0. Zero Slop owns the meter, and tracked-fact
checks are narrower than full semantic fidelity. This is not an independent
product ranking. First Reader is review-only and has no invented rewrite score.

## New reader workflow and engineering checks

- Reader helper: 24 automated contract tests, including source/audience binding,
  stop behaviour, notes-only recall, HTML escaping and narrow-screen layout.
- First Reader comparison: 32/32 constructed offline component checks at the
  pinned upstream revision; ten comparison regression tests. No upstream model
  session or human reader study was run.
- Full Python suite: 432 passed, one skipped, 433 run. Additional compatibility
  tests: eight passed. CLI contract suite: 49 passed. Gateway: 97 passed.
- Responsive report checked at 320, 375, 768 and 1,440 pixels. Website: 705 tests
  passed plus responsive/reduced-motion browser checks. Emulation, not physical
  phone certification or production load testing.

See [delivery evidence](reader-review-delivery.md) for scope and independent
review. The next effectiveness experiment is a matched, blinded audience study
with the same drafts, models and budgets, independent human labels, and
predeclared outcomes. See [the research plan](../bench/first-reader/RESEARCH.md).

## Reproduce

Run from the repository root. Use an empty temporary `ZERO_SLOP_HOME` when
reproducing public scorer results so private corrections cannot affect them.
Network commands fetch public corpus data; they make no inference calls.

```sh
python3 scripts/calibrate.py --selftest
python3 bench/discrimination/evaluate.py
python3 bench/search-corpus/evaluate.py --check
python3 bench/antithesis/evaluate.py --check
python3 bench/quality-corpus/build_manifest.py --check
python3 bench/quality-corpus/evaluate.py \
  --manifest bench/quality-corpus/manifest.json \
  --labels bench/quality-corpus/labels-rater-a.json \
  --labels bench/quality-corpus/labels-rater-b.json \
  --out bench/quality-corpus/results.json --check
python3 bench/search-corpus/compare.py --check
python3 bench/raid-plus-corpus/audit.py --fetch --check
python3 bench/beemo-corpus/audit.py --fetch --check
```

The last command is expected to report stale saved aggregates until a separately
reviewed benchmark refresh is made. A non-fetch `--check` validates only the
saved result contract; it is not a replacement for rescoring the external data.
