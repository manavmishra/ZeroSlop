# Zero Slop: AI Writing Editor and Slop Detector

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-202521">
  <img alt="tests" src="https://img.shields.io/badge/tests-CI%20gated-227B5B">
  <img alt="dependencies" src="https://img.shields.io/badge/runtime%20dependencies-0-227B5B">
  <img alt="privacy" src="https://img.shields.io/badge/learning-private-227B5B">
  <img alt="version" src="https://img.shields.io/badge/version-2.5.1-72528F">
</p>

**Less slop, more pop in all your writing.**

Zero Slop is an open-source Agent Skill for editing AI slop: stock phrasing, claims
without evidence, uniform cadence, and formulaic structure in AI-assisted writing. It
revises the draft without changing its claims, voice, or format. It works with Claude
Code, Codex, Cursor, and other Agent Skills-compatible assistants.

The 0-to-100 score measures those signals, not AI authorship. In the shipped reference
sets, human samples scored 9 to 21; unedited AI drafts averaged 77. The figures apply
only to that corpus.

![A scored sentence before and after editing](assets/demo.png)

## Install Zero Slop

Paste this into Claude Code, Codex, Cursor, OpenCode, Warp, Zed, or another
Agent Skills-compatible assistant:

```text
Install or update Zero Slop from https://github.com/manavmishra/ZeroSlop for
this agent.

1. Find active installations. Report each path, version, and method. Do not duplicate
   or remove one without asking.
2. For updates, keep the existing install method. In Codex, use $skill-installer for
   `skills/zero-slop`; in Claude Code or Cowork, use the plugin marketplace. Otherwise
   use `npx skills add manavmishra/ZeroSlop --global` to install or
   `npx skills update zero-slop --global` to update.
3. Preserve ZERO_SLOP_HOME (default: ~/.zero-slop) and its private data.
4. Verify the version. When Python is available, run
   `python3 scripts/calibrate.py --selftest`.
5. Report the path, method, version, validation result, and restart requirement.

Do not modify the current project or unrelated configuration. Ask before falling
back to a project-local installation.
```

Direct terminal install:

```bash
npx skills add manavmishra/ZeroSlop --global
```

Claude Code and Cowork can use `/plugin marketplace add manavmishra/ZeroSlop`, then
`/plugin install zero-slop@zero-slop`. ChatGPT users can download
[`dist/zero-slop-single-file.md`](dist/zero-slop-single-file.md); Claude.ai users can
use the release zip.

## How Zero Slop works

![One production path, two operational loops, and an independent release gate](assets/engine.svg)

Production follows six steps:

1. **Measure.** Local Python scores 267 weighted patterns, a 96-term lexicon, 25
   context-gated terms, cadence, readability, formatting, and register. It reports the
   evidence behind the result.
2. **Interpret.** The host AI assistant evaluates claims, evidence, audience,
   structure, and voice. It asks for missing facts rather than inventing them.
3. **Rewrite.** The assistant removes generic wording, then revises order, cadence,
   and tone. Relevant private preferences can guide the edit.
4. **Select.** A local reranker rejects versions that change the factual inventory,
   then chooses the cleanest remaining option.
5. **Edit.** A copy editor corrects mechanics. A separate read-aloud pass resolves
   awkward flow, inconsistency, and repetition.
6. **Verify.** The result is rescored and compared with the source for facts, meaning,
   qualifiers, voice, format, and structure. A repair repeats every final check.

The scripts use only Python's standard library and do not send drafts over the
network. Predictability and cross-draft repetition are reported separately from the
surface score. `scripts/contextual.py` is a research tool, not a second runtime mode.

## Private learning from writer edits

Learning starts only when Zero Slop receives both the version it produced and the
version the writer kept. It never monitors files, browsers, or publishing systems.
Each observation includes hashes, an editorial reason, and the genre.

A phrase needs evidence from three distinct documents before it can become a private
rule; a single word requires five. Every rule must pass the known-human safety set.
Recurring replacements guide later edits, retained phrases can lower a matching rule's
weight, and stale rules decay. The private overlay lives under `$ZERO_SLOP_HOME`. It is
reversible and does not retrain or modify the AI model.

## Evaluation, evidence, and limits

Operational tests check whether the software behaves as specified. Editorial research
asks whether the result reads better. Neither supports a universal accuracy score.

Two independent LLM editorial raters reviewed 72 method-hidden passages from 12 drafts
using one rubric. Exact agreement was 77.8%; Cohen's kappa was 0.65. They reached a
shared label for 38 passages and left 34 unresolved. Mean severity fell from 4.75 for
the unedited drafts to 2.38 for Zero Slop. This small study does not replace human
evaluation.

![Mean editorial severity assigned by two LLM raters; lower is better](assets/bench-blind-quality.png)

An older study recorded 55 of 100 best picks for Zero Slop, versus 40 for humanizer. Its
two passes agreed on 26 of 50 winners; Cohen's kappa was 0.12. The 95% Wilson interval
was 45.2% to 64.4%, and the head-to-head gives p = 0.15. Because the model settings
were not preserved, this is historical context rather than a current performance
claim.

The v2.5.1 scorer matched v2.4.3 exactly across 152 documents. In a separate 22-item
experiment, a research-only contextual review agreed with another LLM rater on 95.45%
of eligible items, compared with 79.54% for the surface score. This measures agreement
between LLMs, not people, so contextual review remains outside production.

![Production scoring remained unchanged; contextual research improved agreement on a small LLM-rated panel](assets/bench-contextual-ablation.png)

The table compares five editing workflows on the same 18 deliberately obvious drafts
across six genres. Each output is tested against Zero Slop's published gates, making
this a reproducible regression test rather than an independent ranking.

| Method | Mean score ↓ | Full gate | Fact inventory | Mean word change |
|---|---:|---:|---:|---:|
| Original drafts | 78.2 | 0/18 | — | — |
| Zero Slop | 15.4 | 18/18 | 18/18 | -26.4% |
| humanizer | 24.3 | 13/18 | 18/18 | -25.7% |
| stop-slop | 24.7 | 13/18 | 18/18 | -34.4% |
| no-ai-slop | 28.5 | 12/18 | 18/18 | -28.0% |
| de-slop | 54.3 | 6/18 | 18/18 | -18.5% |

![Results of the same 18-draft replay; lower scores are cleaner on Zero Slop's meter](assets/bench-search-rewrites.png)

No available corpus supports a field-accuracy claim. That requires independent human
labels on samples from current models and varied writing, including work by non-native
speakers. AIStoryHub, Beemo, and the Slop Index remain limited cross-checks documented
in [`bench/README.md`](bench/README.md).

On the recorded Darwin arm64 run, scoring 1,000 documents took 2.4986 s; 400.2 docs/s.
A 15,201-word document took 0.3526 s, the worst pathological input took 2.4453 s, and
an 8,000-word reflection took 0.1478 s. These are measurements from one machine, not
service-level guarantees.

## What Zero Slop adds

Zero Slop builds on [no-ai-slop](https://github.com/petergyang/no-ai-slop),
[humanizer](https://github.com/blader/humanizer),
[de-slop](https://github.com/isatimur/de-slop), and
[stop-slop](https://github.com/hardikpandya/stop-slop). It adds scoring, factual
checks, dedicated editorial passes, private learning, and release controls.

The audit compares documented capabilities, not effectiveness, at these versions: Zero
Slop `3790a1f08ebe`, humanizer `e2e92e7b4b82`, and no-ai-slop `d30eddb9e045`.

![Pinned repository capability audit](assets/competitor-capabilities.png)

## Reproduce the tests and benchmarks

```bash
python3 tests/test_all.py
python3 scripts/calibrate.py --selftest
python3 bench/search-corpus/compare.py --check
python3 bench/quality-corpus/evaluate.py --manifest bench/quality-corpus/manifest.json \
  --labels bench/quality-corpus/labels-rater-a.json \
  --labels bench/quality-corpus/labels-rater-b.json \
  --out bench/quality-corpus/results.json --check
python3 bench/feature-ablation/check.py
python3 bench/validate_corpus_registry.py
python3 bench/make_charts.py --check
```

`SKILL.md` defines the runtime. `scripts/` contains the meter, fidelity check,
reranker, and private learning tools. `references/` contains the editorial briefs.
`bench/` contains the pinned inputs, saved outputs, raw labels, limits, and aggregation
code. See [`SECURITY.md`](SECURITY.md) for trust boundaries and
[`references/evidence.md`](references/evidence.md) for the research trail.

MIT.
