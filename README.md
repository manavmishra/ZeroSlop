# Zero Slop: AI Writing Editor and Slop Detector

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-202521">
  <img alt="tests" src="https://img.shields.io/badge/tests-passing-227B5B">
  <img alt="dependencies" src="https://img.shields.io/badge/runtime%20dependencies-0-227B5B">
  <img alt="privacy" src="https://img.shields.io/badge/learning-private-227B5B">
  <img alt="version" src="https://img.shields.io/badge/version-2.5.9-72528F">
</p>

**Less slop, more pop.**

Zero Slop is an Agent Skill, not an AI model. Claude, GPT, or another compatible
model inside your AI assistant edits the draft. Zero Slop supplies the workflow
and local checks that protect the source.

Its 0-to-100 writing score points to flagged phrases, flat rhythm, dense passages,
and distracting formatting. It does not estimate authorship. In the references,
human writing scored from 9 to 21; unedited AI drafts averaged 77. These are
comparisons, not universal cutoffs.

![A scored sentence before and after editing](assets/demo.png)

## Install Zero Slop

Paste this prompt into Claude Code, Codex, Cursor, OpenCode, Warp, Zed, or another
Agent Skills-compatible assistant:

```text
Install or update Zero Slop from https://github.com/manavmishra/ZeroSlop for
this agent.

1. Find active installations. Report each path, version, and method. Do not duplicate
   or remove one without asking.
2. Keep the current install method when updating. In Codex, use $skill-installer for
   `skills/zero-slop`; in Claude Code or Cowork, use the plugin marketplace. Otherwise
   use `npx skills add manavmishra/ZeroSlop --global` for a first install or
   `npx skills update zero-slop --global` for an existing CLI install.
3. Preserve ZERO_SLOP_HOME (default: ~/.zero-slop) and its private data.
4. Verify the installed version. When Python is available, run
   `python3 scripts/calibrate.py --selftest` from the installed skill directory.
5. Report the path, method, version, validation result, and restart requirement.

Do not modify the current project or unrelated configuration. Ask before falling
back to a project-local installation.
```

Direct terminal install:

```bash
npx skills add manavmishra/ZeroSlop --global
```

ChatGPT users can download [`dist/zero-slop-single-file.md`](dist/zero-slop-single-file.md);
Claude.ai users can download the ZIP.

## How it works

![Seven editorial roles, a private learning loop, and a separate release review](assets/engine.svg)

Seven roles form one workflow. They are jobs, not separate models. Your AI assistant
handles the editorial judgment; local Python tools make the repeatable checks.

| Role | Who does it | What happens |
|---|---|---|
| 1. Scorer | Local tools | Finds the exact wording, rhythm, readability, and formatting problems that raised the writing score. |
| 2. Interpreter | Your AI assistant | Reads the claims, purpose, audience, structure, and voice before changing anything. |
| 3. Rewriter | Your AI assistant | Removes stock language and rebuilds order, rhythm, and tone without inventing detail. |
| 4. Fact gate | Local tools | Rejects a version that changes names, numbers, quotations, links, code, tables, paths, or document structure. |
| 5. Copy desk | Fresh AI pass | Corrects grammar, spelling, usage, and consistency in the actual deliverable. |
| 6. Read-aloud editor | Fresh AI pass | Fixes stumbles, repetition, weak transitions, and awkward flow. |
| 7. Verifier | Local tools and your AI assistant | Compares the finished text with the source for facts, meaning, qualifiers, voice, format, and structure. Any repair repeats both editorial passes and every final check. |

Research supports the checks, not the number seven. Studies find
[predictable wording](https://arxiv.org/abs/2301.11305) and
[overused vocabulary](https://arxiv.org/abs/2406.07016) in machine text, while
authorship detectors can [misclassify non-native English](https://arxiv.org/abs/2304.02819).
Zero Slop combines language checks with contextual editing and keeps the rewriter
from certifying its own work. Local tools use only Python's standard library.

## Private learning from your edits

Learning starts only when you provide both the assistant's version and the version
you kept. Zero Slop never watches files, browsers, or publishing systems.

A phrase needs removal from three unrelated pieces before it becomes a private rule;
a single word needs five. Each rule must be new and safe on known-human text.
Repeated fixes guide later edits; kept phrases can quiet a rule. The private file lives under
`$ZERO_SLOP_HOME`. This is human-in-the-loop online learning, not neural training or
RLHF, and it never retrains Claude, GPT, or another model.

A profile can exempt existing watchlist words when selected by name. It does not
learn cadence, tone, or a complete writing style.

## What v2.5.9 proved

The release adds hidden-character and mixed-script normalization, broader AI-tool
tracking residue, chat role-play actions, a cautious long-document check, and
protection for code, front matter, tables, headings, and file paths. Against v2.5.8,
it changed none of the 114 frozen document
scores, kept all 18 known-human controls below the release gate, and matched the
84.2% result on the 38-item editorial panel. It caught every new edge case in the
version test and blocked all four tested classes of structured-document damage.
The 12-run interleaved speed check measured 0.41% higher median throughput. This is
why v2.5.9, rather than v2.5.8, is the recommended release.

### Fresh same-model editing replay

We reran Zero Slop, [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing),
[no-ai-slop](https://github.com/petergyang/no-ai-slop), and
[humanizer](https://github.com/blader/humanizer) from scratch on the same 18 obvious
drafts. Every workflow used GPT-5.4, high reasoning, batches of three, and its pinned
instruction file.

| Method | Mean writing score ↓ | Passed all Zero Slop checks | Important details kept | Average length change |
|---|---:|---:|---:|---:|
| Original drafts | 76.3 | 0/18 | — | — |
| Zero Slop | 12.8 | 18/18 | 18/18 | -8.9% |
| avoid-ai-writing | 23.3 | 15/18 | 18/18 | -14.6% |
| no-ai-slop | 28.4 | 12/18 | 17/18 | -13.7% |
| humanizer | 35.4 | 9/18 | 17/18 | -7.2% |

![Fresh same-model editing replay on 18 drafts](assets/bench-search-rewrites.png)

Zero Slop leads this replay on its own checks. The incumbent's meter scored its own
outputs best at 0.0, followed by humanizer at 0.6 and Zero Slop and no-ai-slop at
1.6. That cross-check is useful precisely because it exposes meter ownership. It is
not independent human field accuracy or a universal ranking.

On the separate 38-item method-hidden LLM editorial panel, Zero Slop's fixed gate
matched 84.2% of the consensus labels. The incumbent's published gate matched 31.6%;
a threshold selected on the development split matched 33.3% on the held-out split.
The panel is small, clustered, and labelled by two LLM editorial raters, not people
in the field. The full audit keeps disagreements and limitations visible in
[`bench/README.md`](bench/README.md).

### Current-model and speed checks

The pinned [RAID+](https://huggingface.co/datasets/markstanl/RAID-Plus) sample yielded
7,627 usable generations:

| Model | Texts scored | Mean writing score ↓ | At or above 25 |
|---|---:|---:|---:|
| DeepSeek V3 | 1,995 | 14.5 | 10.1% |
| Gemini 3.1 Pro | 1,998 | 17.0 | 18.2% |
| Gemma 3 27B | 1,634 | 21.6 | 30.4% |
| Llama 3.3 70B | 2,000 | 25.5 | 41.7% |

RAID+ records model origin, not editorial quality. In Beemo, raw model responses
averaged 30.2, expert edits 25.3, and human answers 20.0; neither dataset has quality
labels.

On one Apple silicon Mac, the local checker processed 1,000 documents in 2.0566
seconds, or 486.2 per second. A 15,201-word document took 0.3134 seconds; the slowest
stress case took 2.4852 seconds. An 8,000-word learning pass took 0.1622 seconds.
These measurements exclude the AI assistant's editing time and are not service-level
guarantees.

## What Zero Slop adds

Zero Slop builds on no-ai-slop, humanizer, de-slop, stop-slop, unslop-text, and
avoid-ai-writing. It adds a writing score, source protection, separate editorial
passes, private learning, portfolio analysis, and release tests. The chart records
documented features, not which tool writes better.

![Documented capabilities at pinned repository versions](assets/competitor-capabilities.png)

Reproduce the shipped checks with `python3 tests/test_all.py`,
`python3 scripts/calibrate.py --selftest`, and `python3 bench/make_charts.py --check`.
The benchmark registry, source pins, scripts, hashes, and limitations are documented
in [`bench/README.md`](bench/README.md).

Released under the [MIT License](LICENSE), which permits commercial and private use,
modification, and redistribution under its terms.
