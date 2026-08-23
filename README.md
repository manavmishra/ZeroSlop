# Zero Slop: AI Writing Editor and Slop Detector

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-202521">
  <img alt="tests" src="https://img.shields.io/badge/tests-passing-227B5B">
  <img alt="dependencies" src="https://img.shields.io/badge/runtime%20dependencies-0-227B5B">
  <img alt="privacy" src="https://img.shields.io/badge/learning-private-227B5B">
  <img alt="version" src="https://img.shields.io/badge/version-2.5.5-72528F">
</p>

**Less slop, more pop in all your writing.**

Zero Slop is an Agent Skill, not an AI model. Claude, GPT, or another compatible model
in your assistant edits the draft; Zero Slop supplies the method and local checks. The
assistant removes generic language without changing meaning, voice, or format.

The 0-to-100 writing score tracks generic AI-style language and lists flagged phrases;
it does not identify the author. In the test sets, human samples scored 9 to 21;
unedited AI drafts averaged 77. These are reference points, not universal boundaries.

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

Claude Code and Cowork can install from the plugin marketplace. ChatGPT users can
download [`dist/zero-slop-single-file.md`](dist/zero-slop-single-file.md); Claude.ai
users can use the release zip.

## How Zero Slop works

![One editing workflow, a private learning loop, and a separate release review](assets/engine.svg)

Seven roles form one workflow. They are jobs, not separate models. Claude, GPT, or
another compatible model handles the editorial passes; local Python tools run
repeatable checks. No Zero Slop AI service receives the draft.

| Role | Who does it | What it does |
|---|---|---|
| 1. Scorer | Local tools | Finds exact phrases, mechanical rhythm, dense passages, and distracting formatting; explains the writing score. |
| 2. Interpreter | Your AI assistant | Reads claims, support, audience, structure, and voice before editing. |
| 3. Rewriter | Your AI assistant | Removes stock wording and improves order, rhythm, and tone without inventing detail. |
| 4. Fact gate | Local tools | Rejects versions that add or drop names, numbers, quotations, or links; selects the clearest one left. |
| 5. Copy desk | Fresh AI pass | Corrects grammar, spelling, usage, and consistency. |
| 6. Read-aloud editor | Fresh AI pass | Fixes stumbles, repetition, weak transitions, and awkward flow. |
| 7. Verifier | Local tools and your AI assistant | Compares the final text with the source for facts, meaning, voice, format, and structure. A repair repeats both editorial passes and every check. |

### Why separate the work?

The roles reflect the work. Research supports the checks, not the number seven.
Studies find
[predictable wording](https://arxiv.org/abs/2301.11305) and
[excess vocabulary](https://arxiv.org/abs/2406.07016) in machine text, while detectors can
[misclassify non-native English](https://arxiv.org/abs/2304.02819). The rewriter therefore
does not certify its own facts, and separate editorial passes catch later errors. Local
tools use Python's standard library and never send drafts. [Research notes](references/evidence.md)
cover the rationale and limits.

## Private learning from writer edits

Learning requires the assistant's version and the writer's final version.
Zero Slop never monitors files, browsers, or publishing systems.

A named profile exempts existing watchlist words found in your sample. One exact
match is enough. It works only when selected by name and does not learn cadence,
tone, or a complete writing style, including syntax, humor, or arbitrary phrases.

A phrase must be cut from three unrelated pieces before becoming a private rule;
single-word cuts need five unrelated pieces. Each proposal must leave human writing
unflagged. Repeated replacements guide edits, phrases
the writer keeps can quiet a rule, and old rules fade. Private, reversible rules under
`$ZERO_SLOP_HOME` never retrain the AI model.

## What the current release measured

Every score and timing was recomputed with v2.5.5, including the corpus audits,
tables, and charts. Saved LLM selections from an older study are not reused.

### Recent model output: RAID+

[RAID+](https://huggingface.co/datasets/markstanl/RAID-Plus) is an MIT-licensed extension
of the peer-reviewed RAID benchmark. We scored its 8,000 pinned rows; 7,627 abstracts
remained after excluding failed or empty generations.

| Model | Texts scored | Mean writing score ↓ | At or above 25 |
|---|---:|---:|---:|
| DeepSeek V3 | 1,995 | 15.2 | 12.0% |
| Gemini 3.1 Pro | 1,998 | 18.9 | 23.9% |
| Gemma 3 27B | 1,634 | 24.2 | 36.1% |
| Llama 3.3 70B | 2,000 | 26.9 | 43.7% |
| **Overall** | **7,627** | **21.2** | **28.6%** |

![Current Zero Slop writing scores across four RAID+ model families](assets/bench-raid-plus.png)

RAID+ records model origin, not editorial quality, so this is a score distribution,
not an accuracy claim. A fresh run on all 2,187 Beemo records found means of 32.0 for
raw model responses, 26.4 for expert edits, and 20.6 for independent human answers.
Expert editing lowered the score in 52.7% of pairs. Beemo also lacks quality labels.

### Five workflows, one fixed set of drafts

We reran v2.5.5's checks on preserved rewrites of 18 generic drafts. One August 23
session produced them using Zero Slop 2.4.3 and pinned competitor instructions; they
were not regenerated. Passing requires clean writing and layout with no altered facts
or invented feelings.

| Method | Mean writing score ↓ | Passed all checks | Automated fact check | Average length change |
|---|---:|---:|---:|---:|
| Original drafts | 78.2 | 0/18 | — | — |
| Zero Slop | 15.4 | 18/18 | 18/18 | -26.4% |
| humanizer | 24.3 | 13/18 | 18/18 | -25.7% |
| stop-slop | 24.7 | 13/18 | 18/18 | -34.4% |
| no-ai-slop | 28.5 | 12/18 | 18/18 | -28.0% |
| de-slop | 54.3 | 6/18 | 18/18 | -18.5% |

![The same 18 drafts after each editing workflow; lower scores mean fewer generic AI-style patterns](assets/bench-search-rewrites.png)

All 18 Zero Slop edits passed, but Zero Slop defines the rules and those rewrites
predate this release. No available set combines current writing with independent human
review, so no universal accuracy number exists. See [`bench/README.md`](bench/README.md).

### The local tools are fast

On one Apple silicon Mac, the local checker processed 1,000 documents in 2.6047 seconds
(383.9 per second). A 15,201-word document took 0.3676 seconds; the slowest stress case
took 2.6362 seconds. An 8,000-word learning pass took 0.1623 seconds. AI-assistant time
is excluded.

## What Zero Slop adds

Zero Slop builds on [no-ai-slop](https://github.com/petergyang/no-ai-slop),
[humanizer](https://github.com/blader/humanizer), [de-slop](https://github.com/isatimur/de-slop),
and [stop-slop](https://github.com/hardikpandya/stop-slop). It adds a local writing
score, fact protection, separate editorial passes, private learning, and release tests.

The chart records documented features in pinned repository versions. It does not
decide which tool writes better. Details are in [`bench/README.md`](bench/README.md).

![Comparison of features documented in pinned repository versions](assets/competitor-capabilities.png)

## Reproduce the tests and benchmarks

```bash
python3 tests/test_all.py
python3 scripts/calibrate.py --selftest
python3 bench/search-corpus/compare.py --check
python3 bench/raid-plus-corpus/audit.py --check
python3 bench/beemo-corpus/audit.py --check
python3 bench/validate_corpus_registry.py
python3 bench/make_charts.py --check
```

`SKILL.md` defines the skill; `scripts/` holds the local tools; `bench/` holds test
inputs and results. See the [security policy](SECURITY.md) for privacy and the
[research notes](references/evidence.md) for sources.

Released under the [MIT License](LICENSE).
