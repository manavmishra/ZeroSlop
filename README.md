# Zero Slop

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-202521">
  <img alt="tests" src="https://img.shields.io/badge/tests-CI%20gated-227B5B">
  <img alt="dependencies" src="https://img.shields.io/badge/runtime%20dependencies-0-227B5B">
  <img alt="privacy" src="https://img.shields.io/badge/learning-private-227B5B">
  <img alt="version" src="https://img.shields.io/badge/version-2.5.1-72528F">
</p>

Zero Slop is an editorial skill for prose written with AI assistance. It finds stock
language, thin claims, repeated shapes, and overworked formatting, then edits the
draft without changing what the writer meant. A local scorer cites visible surface
evidence. The host language model supplies contextual judgment and performs the edit.
Fresh copy-editing and read-aloud passes polish the exact text returned to the reader.

The 0-to-100 score measures a register, not the probability that AI wrote the text.
In the shipped reference sets, known-human writing lands between 9 and 21; raw AI
drafts average 77. These are calibration anchors, not universal boundaries.

![A scored sentence before and after editing](assets/demo.png)

## Install with an agent

Paste this into Claude Code, Codex, Cursor, OpenCode, Warp, Zed, or another
Agent Skills-compatible assistant:

```text
Install or update Zero Slop from https://github.com/manavmishra/ZeroSlop for
this agent.

1. Find every active Zero Slop installation. Report each path, version, and install
   method. Do not create a duplicate or delete an installation without asking.
2. Keep the existing install method when updating. In Codex, invoke
   $skill-installer and install only the repository path `skills/zero-slop`; do not
   also install the root source copy. In Claude Code or Cowork, use the plugin
   marketplace. Otherwise use `npx skills add manavmishra/ZeroSlop --global` for a
   first install or `npx skills update zero-slop --global` for an existing CLI install.
3. Preserve ZERO_SLOP_HOME (default: ~/.zero-slop). It contains private learning and
   voice data. Never overwrite it or copy it into the skill directory.
4. Install SKILL.md, references/, scripts/, and data/. Verify the installed version
   against the repository, confirm every required path exists, and run
   `python3 scripts/calibrate.py --selftest` when Python is available.
5. Report the exact install path, method, version, validation result, and whether a
   restart or new session is required. Do not claim success before verification.

Do not modify the current project or unrelated configuration. Ask before falling
back to a project-local installation.
```

Direct terminal install:

```bash
npx skills add manavmishra/ZeroSlop --global
```

Claude Code and Cowork can use `/plugin marketplace add manavmishra/ZeroSlop`, then
`/plugin install zero-slop@zero-slop`. ChatGPT users can download
[`dist/zero-slop-single-file.md`](dist/zero-slop-single-file.md). Claude.ai users can
upload the single-skill zip attached to the
[latest release](https://github.com/manavmishra/ZeroSlop/releases/latest), or build the
zip with `python3 scripts/build_skill_zip.py`.

## How it works

![One production path, two operational loops, and an independent release gate](assets/engine.svg)

One workflow combines local measurement with contextual editing:

1. **Measure:** local Python reports a repeatable surface score and exact hits.
2. **Diagnose:** the host model reads claims, substance, audience, genre, structure,
   and voice. Every finding stays tied to the current draft; missing context calls for
   an abstention, not a guess.
3. **Rewrite:** the model cuts, repairs, or reorders; fidelity outranks cleanliness.
   Relevant, reason-labelled preferences may guide the edit; when none matches, the
   model abstains.
4. **Copy edit:** a fresh editor fixes grammar, spelling, punctuation, diction, and
   consistency in the deliverable itself.
5. **Read aloud:** another fresh pass fixes flow, cohesion, repetition, and rough joins.
6. **Verify:** scripts and the host model recheck score, facts, meaning, qualifiers,
   voice, format, and structure. Any textual repair repeats both editorial passes and
   every final check.

There is one production workflow. Contextual experiments stay in the
maintainer release-research lane and are not installed as live features.

The local meter combines weighted phrases and context-gated terms with rhythm,
followability, formatting, and register signals. Predictability and cross-draft
portfolio repetition stay separate from the score. The scripted fidelity check covers
names, figures, quotations, and links; semantic review protects claims, qualifiers,
voice, and non-prose structure.

Useful local commands:

```bash
python3 scripts/slopscore.py --explain draft.md
python3 scripts/slopscore.py --gate 25 draft.md
python3 scripts/slopscore.py --fidelity draft.md rewrite.md
python3 scripts/slopscore.py --portfolio drafts/
python3 scripts/learn.py --guide --for draft.md --reason canned_framing --genre email
```

The runtime uses only Python's standard library and calls no network service. Without
Python, the agent follows the written workflow and reports the scripted gates as
unavailable.

## Two loops, with different authority

**Editorial delivery** turns the current draft into finished copy. **Private online
learning** observes later human edits and records each change with exact
before-and-after hashes, its reason, and its genre. It rejects weak evidence, stores a
reversible overlay, and retrieves only relevant guidance on later drafts.

This is post-deployment, human-in-the-loop online adaptation—not reinforcement
learning, RLHF, self-modification, or neural training. One edit pair is one vote. A
phrase needs three content-distinct pairs before promotion; a single word needs five
and stays context-dependent. A proposed rule must be new and safe on known-human text.
Unconfirmed detector weights decay after 18 months; stale fix preferences retire.
Private state lives under `$ZERO_SLOP_HOME`, outside the installation.

The release-research lane is not a runtime loop. It admits corpora, runs blind and
grouped evaluations, and tests performance, fidelity, safety, cost, and subgroup
behavior. New behavior cannot promote itself.

## What the fresh evidence says

There is no defensible field-accuracy number yet. The high-bar release set still needs
independent human slop-quality labels for samples spanning representative genres and
dialects, current models, and writing by non-native speakers. The results below answer
narrower questions.

### Same 18 drafts, five editing methods

One Codex desktop session replayed the pinned instructions on anonymous, deliberately
obvious examples across six genres. The comparison tests complete workflows against
Zero Slop's own surface and shape gates; it is not an independent quality ranking.

| Method | Mean surface score ↓ | Surface + shape + fact pass | Automated fact inventory | Mean word change |
|---|---:|---:|---:|---:|
| Original drafts | 78.2 | 0/18 | — | — |
| Zero Slop | 15.4 | 18/18 | 18/18 | -26.4% |
| humanizer | 24.3 | 13/18 | 18/18 | -25.7% |
| stop-slop | 24.7 | 13/18 | 18/18 | -34.4% |
| no-ai-slop | 28.5 | 12/18 | 18/18 | -28.0% |
| de-slop | 54.3 | 6/18 | 18/18 | -18.5% |

![Fresh instruction replay: lower surface score is cleaner on Zero Slop's meter](assets/bench-search-rewrites.png)

### Small blind quality panel

Two independent agents reviewed a 72-item packet with the methods hidden. They agreed
on a binary label for 38 items and left 34 unresolved rather than forcing labels. Exact
agreement was 77.8%; Cohen's kappa was 0.65. Mean blind severity was 4.75 for the
originals, 4.08 for de-slop, 3.21 for stop-slop, 3.12 for no-ai-slop, 2.88 for
humanizer, and 2.38 for Zero Slop. These are blind LLM-as-a-judge results on a small,
clustered panel—not human field accuracy.

![Blind mean severity by editing method](assets/bench-blind-quality.png)

### Production surface and contextual research

The v2.5.1 production scoring output was bit-for-bit identical to v2.4.3 across
152 documents. Both score-vector hashes were
`7b98680faa19bd5b0d66383d36cc9b12eda26bdd40b1f5bfa32b82c6fbfe6ad8`.
Consensus accuracy of the surface gate stayed 71.05%, a 0.00-point change. On the
small held-out cross-rater panel, source-bound contextual review scored 95.45% against
79.54% for the surface gate on the same eligible items, a 15.91-point lift. Because
the comparison reuses two LLM editorial raters, it measures reproducibility rather
than field accuracy. In a retrieval test, the system found the relevant preference and
abstained on an irrelevant draft; real-user accuracy remains unmeasured.

![The production surface score is unchanged; a separate contextual research review improved agreement on the small blind panel](assets/bench-contextual-ablation.png)

**Production verdict:** ship v2.5.1 with one guarded workflow. Keep contextual review
in release research until a source-grouped holdout independently labelled by humans
shows a material gain without fidelity, subgroup, latency, or cost regression.

### Public cross-check and paired edits

The public [AIStoryHub checker](https://aistoryhub.co/slop-checker) was rerun item by
item. It is a browser-local pattern checker, not a test of facts, meaning, or authorship.

| Text or method | Reads Clean | Eligible | Abstained | Mean checker score ↓ |
|---|---:|---:|---:|---:|
| Original drafts | 3 (16.7%) | 18 | 0 | 80.6 |
| Zero Slop | 15 (88.2%) | 17 | 1 | 11.1 |
| stop-slop | 13 (76.5%) | 17 | 1 | 22.6 |
| humanizer | 13 (72.2%) | 18 | 0 | 26.7 |
| no-ai-slop | 13 (72.2%) | 18 | 0 | 26.7 |
| de-slop | 7 (38.9%) | 18 | 0 | 58.9 |

[Beemo](https://huggingface.co/datasets/toloka/beemo) records model provenance and
human editing history, not slop quality. Its pinned revision `9c014107fe9b` is useful
as an out-of-domain paired stress test:

| Beemo text | Documents | Mean score ↓ | Median score ↓ | At or above the generic 25-point gate |
|---|---:|---:|---:|---:|
| Raw model output | 2,187 | 32.0 | 20.2 | 848 (38.8%) |
| Expert human edit | 2,187 | 26.4 | 20.2 | 604 (27.6%) |
| Independent human answer | 2,187 | 20.6 | 15.8 | 352 (16.1%) |

Expert editing lowered the score for only 52.7% of pairs, a useful warning against
treating a surface meter as a measure of accuracy.

### Corpus admission: a deliberately high bar

Each source listed below is registered in
[`bench/corpus-registry.json`](bench/corpus-registry.json) with its label meaning,
license, provenance, leakage risk, allowed use, and admission tier.

| Tier | Sources | Permitted claim |
|---|---|---|
| Release gate | Zero Slop cross-genre regression corpus | Deterministic regression and same-session comparisons |
| Release research | Internal blind-quality panel, AIStoryHub, Beemo, Slop Index | Narrow, explicitly caveated observations |
| Candidate research | RAID, MAGE, HC3, ARB, MAGA, M4, M4GT-Bench, COLING 2025, AuTextification, Blog Authorship, Enron | Drift and human-safety checks; never slop-quality accuracy |
| Restricted research | EditLens, No Robots, PERSUADE 2.0 | Evaluate only under their access and license terms |
| Discovery only | LLM excess vocabulary, slop-forensics, SlopBench, Wikipedia's signs | Candidate signals; never automatic promotion |

No listed corpus currently clears every field-accuracy requirement. The skill will not
turn authorship labels into quality labels, train on its test split, redistribute
restricted text, or report a hand-shaped score as a calibrated probability.

### Performance and historical context

On Darwin arm64, Python 3.9.6, the current local run scored 1,000 documents in
2.4986 s; 400.2 docs/s. A 15,201-word document took 0.3526 s. The worst pathological
input took 2.4453 s; an 8,000-word reflection took 0.1478 s. Preparing and
validating a 2,000-paragraph contextual research packet took 0.0028 s and
0.0045 s, respectively, excluding host-model latency. All timings are observations
from one machine, not throughput promises.

The repository also preserves two historical blind LLM-as-a-judge passes, although
their exact model and inference settings were not recorded. Running
`bench/replication.py` recomputes the statistics from those saved decisions; it does
not call new judges. Across 100 saved selections, Zero Slop received 55, blader/humanizer 40,
no-ai-slop 5 and de-slop 0. The passes
agreed on the winner for only 26 of 50 items; Cohen's kappa was 0.12. Zero Slop's 55%
rate has a Wilson interval of 45.2% to 64.4%. A comparison of
the 95 selections assigned to Zero Slop or humanizer gives p = 0.15. This is
historical descriptive evidence, not a reproducible winner claim.

<details>
<summary>External model context: all 18 reproduced Slop Index rows</summary>

[The Slop Index](https://github.com/hgaddipati1118/slop-index) commit `f9dc3c757845`
contains 19,928 raw generations. Its mechanical ranking changed under every one of
500 random axis reweightings, so the rows are context rather than a universal ranking.

| Published rank | Model | Mechanical index ↓ | Bootstrap rank range |
|---:|---|---:|---:|
| 1 | mistral-large | 40.6 | 1 |
| 2 | claude-fable-5 | 35.6 | 2–3 |
| 3 | gpt-5.6-terra | 32.8 | 3–6 |
| 4 | claude-opus-4-8 | 31.8 | 3–8 |
| 5 | gpt-5.6-sol | 31.7 | 3–8 |
| 6 | gpt-5.6-luna | 31.7 | 3–8 |
| 7 | glm-5.2 | 31.2 | 4–9 |
| 8 | claude-sonnet-5 | 30.5 | 4–9 |
| 9 | qwen3.7-max | 28.7 | 8–11 |
| 10 | gemini-3.5-flash | 27.8 | 9–12 |
| 11 | gpt-5.4-mini | 26.8 | 9–12 |
| 12 | claude-haiku-4-5 | 24.9 | 12–16 |
| 13 | gemini-3.1-pro-preview | 24.3 | 12–17 |
| 14 | grok-4.5 | 24.1 | 13–17 |
| 15 | deepseek-v4-pro | 23.8 | 8–18 |
| 16 | minimax-m3 | 23.1 | 13–18 |
| 17 | muse-spark-1.1 | 23.1 | 12–18 |
| 18 | kimi-k2p6 | 21.1 | 16–18 |

</details>

## What Zero Slop adds

Zero Slop builds on [no-ai-slop](https://github.com/petergyang/no-ai-slop),
[humanizer](https://github.com/blader/humanizer),
[de-slop](https://github.com/isatimur/de-slop), and
[stop-slop](https://github.com/hardikpandya/stop-slop). It carries forward those
projects' direct editing, broad tell coverage, voice protection, and attention to
rhythm. It adds an explainable meter, source-bound editorial diagnosis, scripted
fidelity checks, fact-preserving rewrite selection, separate copy and read-aloud editors, private
reason-labelled retrieval, cross-draft diagnosis, and a fail-closed release harness
with a separate contextual research tool.

A documented capability does not prove that it works well. The matrix audits repository
contracts, not effectiveness, at these commits: Zero Slop `3790a1f08ebe`, humanizer
`e2e92e7b4b82`, and no-ai-slop `d30eddb9e045`.

![Pinned repository capability audit](assets/competitor-capabilities.png)

## Reproduce and inspect

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

`SKILL.md` defines runtime behavior. `scripts/slopscore.py` and `learn.py` implement
the local meter and private overlay. `references/` holds the editorial briefs.
The maintainer-only `scripts/contextual.py` supports release research; it is excluded
from installed skills. `bench/` contains inputs, outputs, pins,
admission decisions, timings, and chart data. The runtime ships no trained model and
never changes the host model's weights. See [`SECURITY.md`](SECURITY.md) for trust
boundaries and [`references/evidence.md`](references/evidence.md) for the research
trail.

MIT.
