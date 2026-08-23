# Zero Slop

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-202521">
  <img alt="tests" src="https://img.shields.io/badge/tests-CI%20gated-227B5B">
  <img alt="dependencies" src="https://img.shields.io/badge/runtime%20dependencies-0-227B5B">
  <img alt="privacy" src="https://img.shields.io/badge/learning-private-227B5B">
  <img alt="version" src="https://img.shields.io/badge/version-2.5.1-72528F">
</p>

Zero Slop looks for the habits that make AI-assisted writing feel canned: stock
phrases, vague claims, mechanical rhythm, and overworked formatting. It reports those
findings to the host model, which rewrites in context. Copy-editing and read-aloud
passes fix grammar, consistency, and stiff sentences.

Scores run from 0 to 100 and measure those habits, not the likelihood that AI wrote the
text. In the shipped references, human samples scored 9 to 21; unedited AI
drafts averaged 77. These are useful comparisons, not universal rules.

![A scored sentence before and after editing](assets/demo.png)

## Install

Paste this into Claude Code, Codex, Cursor, OpenCode, Warp, Zed, or another
Agent Skills-compatible assistant:

```text
Install or update Zero Slop from https://github.com/manavmishra/ZeroSlop for
this agent.

1. Find each active installation. Report its path, version, and method. Do not create
   a duplicate or remove one without asking.
2. For updates, keep the current install method. In Codex, use $skill-installer and
   install only `skills/zero-slop`. In Claude Code or Cowork, use the plugin
   marketplace. Otherwise use `npx skills add manavmishra/ZeroSlop --global` for a
   first install or `npx skills update zero-slop --global` for an existing CLI install.
3. Preserve ZERO_SLOP_HOME (default: ~/.zero-slop). It holds private learning and
   voice data.
4. Verify the version and files. When Python is available, run
   `python3 scripts/calibrate.py --selftest` from the installed skill directory.
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
[`dist/zero-slop-single-file.md`](dist/zero-slop-single-file.md). The latest release
also includes a single-skill zip for Claude.ai.

## How it works

![One production path, two operational loops, and an independent release gate](assets/engine.svg)

There is one production workflow:

1. **Measure.** Local Python cites the language and structural signals behind the
   score: 267 weighted patterns, a 96-term lexicon, 25 context-gated terms, rhythm,
   followability, formatting, and register.
2. **Diagnose.** The host model checks substance, claims, audience, genre, structure,
   and voice. Missing facts produce questions, not inventions.
3. **Rewrite.** It removes stock wording, then rebuilds order, rhythm, and tone.
4. **Choose.** A local reranker rejects invented facts first, then selects the version
   that best clears the measured gates.
5. **Finish.** Separate copy-editing and read-aloud passes fix mechanics, flow, and
   repetition.
6. **Verify.** The final text is rescored and checked against the source for facts,
   meaning, qualifiers, voice, format, and structure. A repair restarts the final
   editorial and verification loop.

The meter is local and explainable; context comes from the host model. Runtime scripts
use only Python's standard library and never send drafts over the network.
`scripts/contextual.py` is research, not a second production mode.

## Private online learning

Learning starts only when the agent sees both its version and the version the writer
kept; nothing watches files, browsers, or publishing platforms. Each pair is hashed
with its reason and genre. A phrase needs three content-distinct pairs before becoming
a private rule; a word needs five. Every rule must be new and safe on known-human text.
Repeated fixes become guidance, retained phrases lower weights, and stale rules decay.

Private state lives under `$ZERO_SLOP_HOME`, outside the installation. This is
human-in-the-loop adaptation, not RLHF, neural training, or self-modifying code.

## Evidence and LLM review

Zero Slop uses independent LLM editorial raters only in release research. They score
saved, method-hidden passages against a fixed rubric; they never affect production or
learning.

The current panel has 72 passages from 12 drafts. Exact agreement was 77.8%; Cohen's
kappa was 0.65. The raters resolved 38 items and left 34 unresolved. Mean severity was
4.75 for the originals and 2.38 for Zero Slop. This small panel does not measure human
field accuracy.

![Mean editorial severity assigned by the two LLM raters; lower is better](assets/bench-blind-quality.png)

Lower bars mean less editing was needed. The sample is too small for an accuracy claim.

An older study gave Zero Slop 55 of 100 best picks, versus 40 for humanizer. Its two
passes agreed on 26 of 50 winners; Cohen's kappa was 0.12. The Wilson interval was
45.2% to 64.4%, and the head-to-head gives p = 0.15. Because the rater configuration
was not preserved, this is historical context, not a winner claim.

Production scoring also stayed bit-for-bit unchanged from v2.4.3 across 152 documents.
On 22 held-out items, the research-only contextual review agreed with the other LLM
rater 95.45% of the time, versus 79.54% for the surface gate. That is cross-rater
repeatability, not human accuracy, so contextual review remains outside production.

![Production scoring stayed unchanged while contextual research improved agreement on the small LLM-rated panel](assets/bench-contextual-ablation.png)

Separate from those panels, the fresh comparison uses 18 deliberately obvious drafts
across six genres. It tests each workflow against Zero Slop's gates, so it is a
regression check, not an independent ranking.

| Method | Mean score ↓ | Full gate | Fact inventory | Mean word change |
|---|---:|---:|---:|---:|
| Original drafts | 78.2 | 0/18 | — | — |
| Zero Slop | 15.4 | 18/18 | 18/18 | -26.4% |
| humanizer | 24.3 | 13/18 | 18/18 | -25.7% |
| stop-slop | 24.7 | 13/18 | 18/18 | -34.4% |
| no-ai-slop | 28.5 | 12/18 | 18/18 | -28.0% |
| de-slop | 54.3 | 6/18 | 18/18 | -18.5% |

![Fresh instruction replay on the same 18 drafts](assets/bench-search-rewrites.png)

The table and chart show which saved workflows clear Zero Slop's measurable checks on
the same drafts.

There is no field-accuracy number yet. A defensible one requires independent human
labels for samples spanning current models and varied writing, including work by
non-native speakers. AIStoryHub, Beemo, and Slop Index remain narrow cross-checks in
[`bench/README.md`](bench/README.md).

On the recorded Darwin arm64 run, scoring 1,000 documents took 2.4986 s; 400.2 docs/s.
A 15,201-word document took 0.3526 s, the worst pathological input took 2.4453 s, and
an 8,000-word reflection took 0.1478 s. These are local observations, not service-level
guarantees.

## What Zero Slop adds

Zero Slop builds on [no-ai-slop](https://github.com/petergyang/no-ai-slop),
[humanizer](https://github.com/blader/humanizer),
[de-slop](https://github.com/isatimur/de-slop), and
[stop-slop](https://github.com/hardikpandya/stop-slop). It adds measurement,
fact-preserving selection, copy and read-aloud editors, private learning, and a
fail-closed release harness.

Documented capability is not proof of effectiveness. The pinned audit compares
Zero Slop `3790a1f08ebe`, humanizer `e2e92e7b4b82`, and no-ai-slop `d30eddb9e045`.

![Pinned repository capability audit](assets/competitor-capabilities.png)

## Reproduce the results

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
