# Zero Slop: AI Writing Editor and Slop Detector

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-202521">
  <img alt="tests" src="https://img.shields.io/badge/tests-CI%20gated-227B5B">
  <img alt="dependencies" src="https://img.shields.io/badge/runtime%20dependencies-0-227B5B">
  <img alt="privacy" src="https://img.shields.io/badge/learning-private-227B5B">
  <img alt="version" src="https://img.shields.io/badge/version-2.5.1-72528F">
</p>

**Less slop, more pop in all your writing.**

Zero Slop is an open-source Agent Skill that removes AI slop from AI-assisted writing:
stock phrasing, unsupported claims, uniform cadence, and formulaic structure. It
revises the draft without changing its claims, voice, or format. It works with Claude
Code, Codex, Cursor, and other compatible assistants.

The 0-to-100 score measures those signals, not AI authorship. In the shipped reference
sets, human samples scored 9 to 21; unedited AI drafts averaged 77. The figures are
corpus-specific.

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

![One editing workflow, a private learning loop, and a separate release review](assets/engine.svg)

When Zero Slop edits a draft, it follows six steps:

1. **Measure.** A local scorer checks 267 weighted patterns, a 96-term lexicon, 25
   context-gated terms, cadence, readability, formatting, and register. It shows the
   evidence behind the score.
2. **Interpret.** The AI assistant running Zero Slop evaluates claims, evidence, audience,
   structure, and voice. It asks for missing facts rather than inventing them.
3. **Rewrite.** The assistant removes generic wording, then revises order, cadence,
   and tone. Relevant private preferences can guide the edit.
4. **Select.** A local check rejects versions that add or drop names, numbers, quotes,
   or links, then chooses the cleanest remaining option.
5. **Edit.** A copy editor corrects grammar and consistency. A read-aloud pass resolves
   awkward flow and repetition.
6. **Verify.** The result is rescored and compared with the source for facts, meaning,
   qualifiers, voice, format, and structure. A repair repeats every final check.

The scripts use only Python's standard library and do not send drafts over the
network. Separate predictability and cross-draft checks do not affect the score.
`scripts/contextual.py` is for research only.

## Private learning from writer edits

Learning starts only when Zero Slop receives both the version it produced and the
version the writer kept. It never monitors files, browsers, or publishing systems.
Each observation includes hashes, an editorial reason, and the genre.

A phrase needs evidence from three distinct documents before it can become a private
rule; a single word requires five. Every rule must pass the known-human safety set.
Recurring replacements guide later edits, retained phrases can lower a matching rule's
weight, and stale rules decay. The private overlay lives under `$ZERO_SLOP_HOME`. It is
reversible and does not retrain or modify the AI model.

## Does Zero Slop work?

Writing quality resists one number. Zero Slop instead publishes narrower tests of
editorial quality, consistent behavior, and speed.

### The clearest signal so far

Two independent LLMs reviewed 72 passages drawn from 12 drafts without
knowing which tool produced them. They labelled each passage clean, borderline, or
sloppy, then assigned severity from 1 (clean) to 5 (pervasively sloppy). The original
drafts averaged 4.75; Zero Slop averaged 2.38.

The raters chose the same label 77.8% of the time. When they disagreed or chose
borderline, the passage was excluded. That left 38 shared clean-or-sloppy decisions
and 34 unresolved cases. The severity gap favors Zero Slop, but the sample is small
and the opinions come from LLMs, not people.

![Average revision severity from two LLM reviewers; lower is better](assets/bench-blind-quality.png)

### Context catches what counting can miss

The score is deliberately literal: it counts visible language and structural signals.
It cannot decide whether a paragraph is useful or whether a phrase fits the audience.
A research-only LLM reviewed 22 passages in context. Its decisions matched another LLM
95.45% of the time, compared with 79.54% for the score alone. Context
appears to help, but the test still compares one LLM with another. The experiment is
not part of the released workflow.

![The experimental context-aware check matched another LLM more often than the mechanical score](assets/bench-contextual-ablation.png)

### The same drafts, edited five ways

The regression test asks whether each workflow behaves consistently. We ran five
workflows on the same 18 deliberately generic drafts. A passage passed only if it met
the score and layout limits and cleared a source check for changed facts or feelings.

| Method | Mean score ↓ | Passed all checks | Automated fact check | Average length change |
|---|---:|---:|---:|---:|
| Original drafts | 78.2 | 0/18 | — | — |
| Zero Slop | 15.4 | 18/18 | 18/18 | -26.4% |
| humanizer | 24.3 | 13/18 | 18/18 | -25.7% |
| stop-slop | 24.7 | 13/18 | 18/18 | -34.4% |
| no-ai-slop | 28.5 | 12/18 | 18/18 | -28.0% |
| de-slop | 54.3 | 6/18 | 18/18 | -18.5% |

Negative length change means the edited draft was shorter.

![The same 18 drafts after each editing workflow; lower scores contain fewer tracked signals](assets/bench-search-rewrites.png)

Zero Slop's edits passed all checks on 18 drafts. That is useful for catching regressions,
but it is not a neutral contest: Zero Slop also defines the rules. No available dataset
combines broad, current writing with independent human quality judgments, so the
project does not publish a universal accuracy number. AIStoryHub, Beemo, and the Slop
Index remain limited cross-checks. See [`bench/README.md`](bench/README.md).

### The local tools are fast

On one Apple silicon Mac, the scorer processed 1,000 documents in 2.4986 seconds
(400.2 per second). A 15,201-word document took 0.3526 seconds. The slowest stress case
took 2.4453 seconds; an 8,000-word learning pass took 0.1478 seconds. AI-assistant time
is excluded.

## What Zero Slop adds

Zero Slop builds on [no-ai-slop](https://github.com/petergyang/no-ai-slop),
[humanizer](https://github.com/blader/humanizer),
[de-slop](https://github.com/isatimur/de-slop), and
[stop-slop](https://github.com/hardikpandya/stop-slop). Those projects established much
of the editorial playbook. Zero Slop adds controls around the edit: a local score,
automated factual checks, separate copy-editing and read-aloud passes, private learning,
and a tested release process.

The chart is an inventory, not a horse race. It records the features documented in
pinned versions of each repository; it does not decide which tool writes better. The
underlying audit is in [`bench/README.md`](bench/README.md).

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

`SKILL.md` defines the runtime. `scripts/` holds the scorer, fidelity check, reranker,
and learning tools. `references/` holds editorial briefs; `bench/` holds test inputs,
labels, results, and methods. See [`SECURITY.md`](SECURITY.md) for trust boundaries and
[`references/evidence.md`](references/evidence.md) for the research trail.

MIT.
