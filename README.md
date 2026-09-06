<p align="center">
  <a href="https://zero-slop.ai">
    <img src="assets/logo/studio/zero-slop-mark-300-transparent.png" width="112" alt="Zero Slop">
  </a>
</p>

Zero Slop crossed 100 GitHub stars and 2,000 npm downloads in its first 12 days.

<h1 align="center">Zero Slop</h1>

<p align="center"><strong>Find AI-sounding writing. Keep the source intact.</strong></p>

<p align="center">
  Zero Slop finds stock phrasing, mechanical rhythm, vague claims, and canned formatting.<br>
  Your existing AI assistant edits the draft; local checks guard its names, numbers, links, quotations, code, tables, and paths.
</p>

<p align="center">
  <a href="https://zero-slop.ai/try/"><strong>Try it in your browser</strong></a>
  ·
  <a href="#install">Install the skill</a>
  ·
  <a href="#evidence-and-limits">See the evidence</a>
  ·
  <a href="https://github.com/manavmishra/ZeroSlop/releases/latest">Latest release</a>
</p>

<p align="center">
  <a href="https://github.com/manavmishra/ZeroSlop/actions/workflows/validate.yml"><img alt="Validate" src="https://github.com/manavmishra/ZeroSlop/actions/workflows/validate.yml/badge.svg"></a>
  <img alt="Version 2.9.0" src="https://img.shields.io/badge/version-2.9.0-72528F">
  <a href="https://www.npmjs.com/package/zero-slop"><img alt="npm version" src="https://img.shields.io/npm/v/zero-slop?color=72528F"></a>
  <a href="https://www.npmjs.com/package/zero-slop"><img alt="npm downloads" src="https://img.shields.io/npm/dm/zero-slop?color=227B5B"></a>
  <a href="https://github.com/manavmishra/ZeroSlop/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/manavmishra/ZeroSlop?style=flat&color=b0442a"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-202521"></a>
  <a href="https://hol.org/guard/plugins"><img alt="Listed in the HOL plugin registry" src="https://img.shields.io/badge/HOL%20registry-listed-2C6E8F"></a>
</p>

```sh
npx skills add manavmishra/ZeroSlop --global
```

<a href="assets/zero-slop-demo.mp4?v=dark-shell-restored-20260906">
  <picture>
    <source media="(prefers-reduced-motion: reduce)" srcset="assets/zero-slop-demo-poster.png?v=dark-shell-restored-20260906">
    <source type="image/webp" srcset="assets/zero-slop-demo.webp?v=dark-shell-restored-20260906">
    <img src="assets/zero-slop-demo.gif?v=dark-shell-restored-20260906" width="900" alt="Dark-shell demo: install Zero Slop, edit with your assistant, and check scores while preserving 40%.">
  </picture>
</a>

<p align="center"><a href="assets/zero-slop-demo.mp4?v=dark-shell-restored-20260906">Watch the 15-second shell demo</a> · <sub>The original demo uses a longer sample than the example below.</sub></p>

## Before and after

A launch post, as AI wrote it:

> We're thrilled to announce that our team has leveraged cutting-edge machine learning to deliver a seamless onboarding experience, reducing setup time by 40%.

The scorer rates that draft 99.3/100 and flags four phrases: “We're thrilled
to,” “leveraged,” “cutting-edge,” and “seamless.”

The rewrite, limited to the draft's stated claims:

> We used machine learning to reduce onboarding setup time by 40%.

```text
Writing score: 9.5/100  [clear]
  Flagged phrases : 0 across 10 words
```

The rewrite retains the draft's stated result. See four complete, reproducible pairs in [`examples/`](examples/).

## What can I use it for?

- Tighten a launch post without losing the release details.
- Turn a padded product update into a useful changelog.
- Clean up an email while preserving names, dates, and numbers.
- Edit a research summary without flattening its qualifications.
- Gate a folder of generated copy before it ships.

Zero Slop is a writing tool. It does not detect authorship; its score describes the text.

## Install

To try Zero Slop first, paste a draft into [zero-slop.ai/try](https://zero-slop.ai/try/). The free editor returns the edit, the before-and-after scores, and the exact phrases that triggered the scorer.

| Environment | Fastest route |
|---|---|
| Claude Code, Codex, Cursor, OpenCode, Warp, Zed | `npx skills add manavmishra/ZeroSlop --global` |
| Gemini CLI | `gemini extensions install https://github.com/manavmishra/ZeroSlop --auto-update` |
| Claude Code plugin | `/plugin marketplace add manavmishra/ZeroSlop`, then `/plugin install zero-slop@zero-slop` |
| Any assistant with file uploads | Download the [single-file bundle](https://github.com/manavmishra/ZeroSlop/releases/latest/download/zero-slop-single-file.md) |
| Claude.ai | Upload the [latest skill ZIP](https://github.com/manavmishra/ZeroSlop/releases/latest/download/zero-slop.zip) |
| ChatGPT, Claude, Grok, Gemini, Cursor, or another MCP client | Connect the optional [hosted MCP server](mcp/README.md) |

Once installed, ask your AI assistant to edit a draft:

```text
/zero-slop (your writing)
```

Inspect a draft without changing it:

```text
/zero-slop inspect (your writing)
```

Score a file locally:

```sh
npx zero-slop score draft.md
```

From a cloned checkout, gate a folder:

```sh
python3 scripts/slopscore.py --batch drafts/ --gate 25
```

Installed checks run locally; editing follows your AI assistant's privacy settings. The optional hosted MCP processes drafts remotely. See its [privacy details](mcp/README.md).

### Prefer one hosted connection? Use the MCP

Connect the [Zero Slop MCP](https://zero-slop.ai/#mcp) once to edit drafts inside your MCP client. Its `deslop` tool returns the edit, before-and-after scores, and review status. Zero Slop requires no account or API key; server updates are managed for you.

```text
https://mcp.zero-slop.ai/mcp
```

See [`DISTRIBUTION.md`](DISTRIBUTION.md) for direct connector commands and directory status.

## What the workflow adds

| A prompt alone | Zero Slop |
|---|---|
| “Make this sound human” leaves the target vague. | A 0–100 meter points to exact phrases and structural problems. |
| One rewrite can quietly alter source details. | A local fact gate checks protected strings before the edit is returned. |
| The model tends to overcorrect into fragments or forced casualness. | An overcorrection pass checks readability, rhythm, grammar, and voice. |
| Each session starts from scratch. | Optional, reason-labelled preferences can be learned privately. |

Zero Slop ships no model. Your AI assistant reads and edits the draft in context,
using Claude, GPT, or another compatible model. The repository supplies the
workflow and local tools for scoring and source checks.

## What it catches

The current scorer combines 294 weighted patterns with a 96-term lexicon. Examples include:

- binary contrast formulas: “It's not X. It's Y.”
- canned openers: “We're thrilled to…” and “Here's the thing…”
- vague attribution: “experts agree” and “studies show”
- significance inflation: “marks a pivotal moment” and “a testament to”
- promotional riders: “robust,” “seamless,” and “leverage” when used as hype
- repeated sentence shapes, crowded statistics, and overworked formatting

Marketing terms are scored in context, so an ordinary technical use of a word need not trigger the same penalty. [`references/eval.md`](references/eval.md) documents all 80 checks.

Unedited AI drafts averaged 77 in [`bench/examples.json`](bench/examples.json).
Human writing scored 9 to 21 in
[`data/corpus/must-not-flag/`](data/corpus/must-not-flag/). These are reference
points for the scorer, not authorship boundaries.

## How it works

![Zero Slop's eight editorial responsibilities, private learning loop, and separate release review](assets/engine.svg)

Eight responsibilities form one workflow. They are jobs, not separate models.
Research supports the checks, not the number eight, which is an engineering
choice.

| Stage | Job |
|---|---|
| 1. Scorer | Find exact phrases, pacing problems, readability issues, and overworked formatting. |
| 2. Interpreter | Read the claims, audience, structure, and voice before editing. |
| 3. Rewriter | Remove stock language without inventing detail. |
| 4. Fact gate | Check names, numbers, quotations, links, code, tables, paths, and structure locally. |
| 5. Copy desk | Fix grammar, usage, spelling, and consistency. |
| 6. Read-aloud editor | Catch stumbles, repetition, and awkward transitions. |
| 7. Verifier | Compare the edit with the source for meaning, qualifiers, voice, and format. |
| 8. Fresh-eyes finalizer | Apply only safe final polish, then run one last local check. |

The free web editor combines the five AI responsibilities into one response and
makes at most one live model call. A single response does not provide independent review.
Any final change receives one final local recheck.

If a repair still misses the target, Zero Slop returns the safest source-preserving edit with a plain warning. It does not enter an open-ended rewrite loop.

## Evidence and limits

### Same model, same 18 drafts

A saved replay ran Zero Slop and three comparable open-source instruction sets over the same drafts with GPT-5.4, high reasoning, and pinned instructions. The outputs are frozen and reproducible.

| Method | Mean writing score ↓ | Passed local gates | Source check passed | Mean length change |
|---|---:|---:|---:|---:|
| Original drafts | 76.3 | 0/18 | — | — |
| **Zero Slop** | **12.8** | **18/18** | **18/18** | -8.9% |
| avoid-ai-writing | 23.3 | 15/18 | 18/18 | -14.6% |
| no-ai-slop | 28.4 | 12/18 | 17/18 | -13.7% |
| humanizer | 35.4 | 9/18 | 17/18 | -7.2% |

![Fresh same-model editing replay on 18 drafts, with lower scores better](assets/bench-search-rewrites.png)

This small LLM-reviewed regression study measures repeatable behavior; it does not establish universal writing quality. The drafts, hashes, method versions, prompts, and limitations are in [`bench/README.md`](bench/README.md).

Zero Slop's frozen outputs came from v2.5.9; newer versions only rescore those
saved outputs. The current scorer matched the prior 84.2% result on the fixed
38-item editorial panel. These fixed-sample checks are not field accuracy.

<details>
<summary>More validation</summary>

- A method-hidden editorial preference replay: [`bench/incumbent-blind-replay/`](bench/incumbent-blind-replay/)
- External-checker clean rates: [`assets/bench-external-checker.png`](assets/bench-external-checker.png)
- Method-hidden quality ranking: [`assets/bench-blind-quality.png`](assets/bench-blind-quality.png)
- Current-model corpus measurements: [`assets/bench-raid-plus.png`](assets/bench-raid-plus.png)
- Antithesis regression set: [`assets/bench-antithesis.png`](assets/bench-antithesis.png)

On the 75 labelled antithesis pairs, the current reading pass reached 91.2% recall across the full set, 100% recall on shapes in reach, and 100% precision. The labels are maintainer-authored and the pairs are constructed, so this is a regression floor rather than field accuracy.

Local speed measurements cover the checks, with editing time excluded. On one
Apple silicon Mac, the scorer processed 1,000 documents in a median of 1.9929
seconds (501.8 per second); the five runs ranged from 1.9614 to 2.0945 seconds.
It scored a 15,201-word document in a median of 0.3223 seconds. The slowest
stress case took 2.2932 seconds, and learning from an 8,000-word edit took
0.1592 seconds. The measurements and machine details are in
[`bench/performance-results.json`](bench/performance-results.json).

Across 12 interleaved runs against 2.7.7, we measured 0.02% lower median throughput,
which is effectively unchanged. The separate two-way replay used
Zero Slop v2.6.0.

The [RAID+ audit](bench/raid-plus-corpus/README.md) checks how the scorer responds
to output from different models. Its pinned sample contains 7,627 usable
generations:

| Model | Texts scored | Mean writing score ↓ | At or above 25 |
|---|---:|---:|---:|
| DeepSeek V3 | 1,995 | 14.5 | 10.1% |
| Gemini 3.1 Pro | 1,998 | 17.0 | 18.2% |
| Gemma 3 27B | 1,634 | 21.6 | 30.4% |
| Llama 3.3 70B | 2,000 | 25.5 | 41.7% |

RAID+ labels record which model produced each text; they do not grade writing
quality. The [Beemo paired-edit audit](bench/beemo-corpus/README.md) checks how
scores change after human editing: raw responses averaged 30.2, expert edits
25.3, and human answers 20.0. Beemo also lacks writing-quality labels.

</details>

### Documented capability audit

![Documented capabilities at pinned repository versions](assets/competitor-capabilities.png)

This chart says nothing about writing quality or which tool writes better. It
records documented features at pinned commits; the data and reproduction notes
are in [`bench/README.md`](bench/README.md).

The design follows research on [predictable wording in machine text](https://arxiv.org/abs/2301.11305) and [overused vocabulary](https://arxiv.org/abs/2406.07016). It deliberately avoids authorship claims because detectors can [misclassify non-native English](https://arxiv.org/abs/2304.02819).

## Private learning

Learning begins only when you provide an original output and your reason-labelled edit. Zero Slop does not monitor files, browsers, or publishing tools. Private data stays under `$ZERO_SLOP_HOME`; it is not committed to this repository and does not retrain the model.

A profile selected by name can exempt existing watchlist words. It does not
learn cadence, tone, or a complete writing style.

## Repository map

| Path | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | The complete detect, rewrite, verify, and learn workflow |
| [`scripts/slopscore.py`](scripts/slopscore.py) | Offline meter and source-detail gate |
| [`scripts/register.py`](scripts/register.py) | Performed-register and reading pass |
| [`references/`](references/) | Genre guidance, tells, safeguards, and evaluation rules |
| [`examples/`](examples/) | Reproducible before-and-after edits |
| [`bench/`](bench/) | Frozen benchmarks, provenance, and limitations |
| [`mcp/`](mcp/) | Optional hosted MCP server documentation |
| [`DISTRIBUTION.md`](DISTRIBUTION.md) | Direct installs, marketplace submissions, and release synchronization |

## Contributing and support

Bug reports, false positives, examples, and carefully tested pattern improvements are welcome. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request, use the structured [issue forms](https://github.com/manavmishra/ZeroSlop/issues/new/choose), or start a [Discussion](https://github.com/manavmishra/ZeroSlop/discussions).

For setup help and responsible disclosure, see [`SUPPORT.md`](SUPPORT.md) and [`SECURITY.md`](SECURITY.md).

## Credits

Zero Slop builds on ideas from [no-ai-slop](https://github.com/petergyang/no-ai-slop), [humanizer](https://github.com/blader/humanizer), [de-slop](https://github.com/isatimur/de-slop), [stop-slop](https://github.com/hardikpandya/stop-slop), [unslop-text](https://github.com/JCarterJohnson/vibecoded-design-tells/tree/main/unslop-ai-text), and [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing).

## License

[MIT](LICENSE)
