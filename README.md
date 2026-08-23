# Zero Slop: AI Writing Editor and Slop Detector

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-202521">
  <img alt="tests" src="https://img.shields.io/badge/tests-passing-227B5B">
  <img alt="dependencies" src="https://img.shields.io/badge/runtime%20dependencies-0-227B5B">
  <img alt="privacy" src="https://img.shields.io/badge/learning-private-227B5B">
  <img alt="version" src="https://img.shields.io/badge/version-2.5.3-72528F">
</p>

**Less slop, more pop in all your writing.**

Zero Slop is an open-source Agent Skill, not an AI model. Claude, GPT, or another
compatible model in your existing assistant reads and edits the draft. Zero Slop
supplies the method and local checks. The assistant removes generic language without
changing meaning, voice, or format. Supported assistants include Claude Code, Codex,
Cursor, and others.

The 0-to-100 writing score shows how much generic AI-style language remains, and the
report names all flagged phrases. It does not identify the author. In the included
test sets, human samples scored 9 to 21; unedited AI drafts averaged 77. These are
reference points for those sets, not universal boundaries.

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

When you use Zero Slop, your AI assistant reads and edits the draft while local
tools run repeatable checks. No separate Zero Slop AI service receives the draft. The
workflow has six steps:

1. **Check the writing.** A local program finds familiar AI-style patterns, mechanical
   rhythm, hard-to-read passages, and distracting formatting. It points to the words
   and structures that raised the writing score.
2. **Read for meaning.** Your AI assistant considers the claims, support, audience,
   structure, and voice. Missing facts prompt questions, not inventions.
3. **Rewrite.** The same assistant removes generic wording, then improves order,
   rhythm, and tone. Preferences learned from earlier writer edits can help.
4. **Protect the facts.** A local check rejects any version that adds or drops names,
   numbers, quotes, or links, then chooses the clearest remaining version.
5. **Polish.** The assistant runs a copy-editing pass for grammar and consistency, then
   a separate read-aloud pass for awkward flow and repetition.
6. **Check again.** The local tools and your assistant compare the final text with the
   source for facts, meaning, voice, format, and structure. Any repair repeats both
   editorial passes and every final check.

The local tools use Python's standard library and never send drafts over the network.
Extra word-guessing and cross-draft checks do not change the writing score.

## Private learning from writer edits

Learning requires both the version returned by the assistant and the version the writer
kept. Zero Slop never monitors files, browsers, or publishing systems.

A phrase must be cut from three unrelated pieces before it becomes a private rule; a
single-word cut requires five unrelated pieces. Each proposal is tested against human
writing that must remain unflagged. Repeated replacements guide later edits, retained
phrases can quiet a rule, and old rules fade. Private rules live under
`$ZERO_SLOP_HOME`; they are reversible and never retrain the AI model.

## Does Zero Slop work?

The published tests cover editorial quality, repeatability, and the speed of the local
tools. No single number can settle writing quality.

### The clearest signal so far

Two independent LLMs reviewed 72 passages from 12 drafts without tool names. They rated
the amount of slop from 1 (clean) to 5 (sloppy throughout). The original drafts averaged
4.75; Zero Slop's edits averaged 2.38.

Agreement was 77.8%. Excluding disagreements and borderline calls left 38 shared decisions and
34 unresolved cases. The gap favors Zero Slop, but the sample is small and the
reviewers are LLMs, not people.

![Average amount of editing needed according to two LLM reviewers; lower is better](assets/bench-blind-quality.png)

### Why context matters

The local check cannot decide whether a paragraph earns its place or suits the
audience. In a 22-passage experiment, an LLM that read the surrounding text agreed
with another LLM 95.45% of the time, versus 79.54% for the writing score alone. This
compares LLMs, not people, and is not part of the installed skill.

![The experimental context-aware check matched another LLM more often than the local writing score](assets/bench-contextual-ablation.png)

### The same drafts, edited five ways

The repeatability test asks whether each workflow behaves consistently. We ran five
workflows on the same 18 deliberately generic drafts. A passage passed only if it met
the score and layout limits and a source check found no altered facts or invented feelings.

| Method | Mean writing score ↓ | Passed all checks | Automated fact check | Average length change |
|---|---:|---:|---:|---:|
| Original drafts | 78.2 | 0/18 | — | — |
| Zero Slop | 15.4 | 18/18 | 18/18 | -26.4% |
| humanizer | 24.3 | 13/18 | 18/18 | -25.7% |
| stop-slop | 24.7 | 13/18 | 18/18 | -34.4% |
| no-ai-slop | 28.5 | 12/18 | 18/18 | -28.0% |
| de-slop | 54.3 | 6/18 | 18/18 | -18.5% |

Negative length change means the edited draft was shorter.

![The same 18 drafts after each editing workflow; lower scores mean fewer generic AI-style patterns](assets/bench-search-rewrites.png)

All 18 drafts edited with Zero Slop passed. That result helps catch unintended changes,
but the comparison is not neutral: Zero Slop defines the rules. No available test set
combines broad, current writing with independent human judgments, so the project does
not publish a universal accuracy number. AIStoryHub, Beemo, and the Slop
Index remain limited cross-checks. See [`bench/README.md`](bench/README.md).

### The local tools are fast

On one Apple silicon Mac, the local checker processed 1,000 documents in 2.4986 seconds
(400.2 per second). A 15,201-word document took 0.3526 seconds. The slowest stress case
took 2.4453 seconds; an 8,000-word learning pass took 0.1478 seconds. AI-assistant time
is excluded.

## What Zero Slop adds

Zero Slop builds on [no-ai-slop](https://github.com/petergyang/no-ai-slop),
[humanizer](https://github.com/blader/humanizer),
[de-slop](https://github.com/isatimur/de-slop), and
[stop-slop](https://github.com/hardikpandya/stop-slop). Those projects established much
of the editorial playbook. Zero Slop adds a local writing score, fact protection,
separate copy-editing and read-aloud passes, private learning, and release tests.

The chart is an inventory, not a horse race. It records the features documented in
pinned versions of each repository; it does not decide which tool writes better. The
comparison details are in [`bench/README.md`](bench/README.md).

![Comparison of features documented in pinned repository versions](assets/competitor-capabilities.png)

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

`SKILL.md` defines the skill. `scripts/` holds tools that check writing and facts,
choose a revision, and learn from edits. `bench/` holds test inputs and results. See
[`SECURITY.md`](SECURITY.md) for privacy details and
[`references/evidence.md`](references/evidence.md) for the research notes.

MIT.
