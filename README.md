# Zero-Slop

**Make it read human. Prove it.**


In 2024, two research teams measured something strange happening to
scientific writing. In AI-conference peer reviews, the word "meticulous" was
appearing at nearly 35 times its expected rate. Across fifteen million
biomedical abstracts, the same style words were surging: "delve,"
"showcase," "intricate." Science had not gotten more careful. Scientists had
started writing with ChatGPT, and ChatGPT has favorite words.

Readers learned the accent fast. On LinkedIn, an em-dash can now get you
accused of outsourcing your thoughts. On Wikipedia, a volunteer cleanup crew
has spent two years cataloguing the tells of machine prose, from "stands as a
testament" to the rhythm of sentences that all run the same length. The
strange part is what the research found underneath: strip away a model's
assistant training and detectors read its raw output as 98 percent human. The
AI voice is not in the machine. It is a style, taught in the final step of
training, and it lives entirely in wording, which means a careful rewrite can
remove it without touching a single fact.

Zero-Slop removes that style and shows you the receipts. It is an AI slop
remover built as an agent skill, with one stubborn rule: every rewrite ships
with before-and-after scores from its built-in detector. No other humanizer
or de-slop tool shows you the numbers.

```bash
npx skills add manavmishra/ZeroSlop --global
```

## A real run, start to finish

This August, a founder drafted a LinkedIn post about two new enterprise-AI
reports. The full draft, as written:

> Enterprise AI value has too often compounded inside individual workflows, leaving a widening gap between the employees building leverage and the organizations trying to scale it.
>
> With OpenAI's State of Enterprise AI report and WRITER's 2026 adoption survey both out, that gap now has numbers. Frontier users send 6x more messages than the median employee, and that's OpenAI's own telemetry, not a survey. Super-users save 9 hours a week against 2 for everyone else. 35% of companies admit they couldn't immediately pull the plug on a rogue agent, and 36% have no formal plan for supervising agents at all. The result shows up in the ROI line: only 29% see significant returns from generative AI, and just 23% from agents, despite 5x individual gains.
>
> OpenAI's own conclusion says the quiet part out loud: the constraint is no longer model performance or tooling. It's organizational readiness. The individual wins are real. What's missing is the boring, unglamorous work that turns them into an operating system for the whole company.
>
> That work has names. Standardization, so the best prompt in the building becomes the default prompt, not a personal stash. AI fluency for the entire org, not certification theater but every function knowing how to shape its own work for a model. Skills and workflows as shared assets with owners and versions. And supervision that scales with autonomy, including the off switch.
>
> The playbook is already inside the building. Your super-users are writing it daily. The work is making it everyone's.
>
> More in both reports below. 👇
>
> #AgenticAI #EnterpriseAI #AIAdoption

No "delve," no rocket emoji in the hook, and the scorer still read it at
45.7: "suspect." The diagnosis was the interesting part. The opener is
announcement voice, an abstraction warming up the crowd while the draft's
best material, a startling statistic, sits buried in paragraph two. The
"quiet part out loud" line is a cliché doing an idea's job. And the hook
promises "two reports" but only ever attaches the 6x to one of them, which
reads oddly hollow without the reader knowing why.

The rewrite, after the full loop:

> 6x. That's how many more messages frontier users send than the median employee, and it's OpenAI's own telemetry in its new State of Enterprise AI report, not a survey.
>
> WRITER's 2026 adoption survey puts the same gap in hours: super-users save 9 a week, everyone else about 2. The control side is worse: 35% of companies admit they couldn't immediately pull the plug on a rogue agent, and 36% have no formal plan for supervising agents at all. The ROI line follows: only 29% see significant returns from generative AI, just 23% from agents, despite 5x individual gains.
>
> OpenAI's report ends on a conclusion you'd expect from a critic, not a vendor: the constraint is no longer the models or the tooling. It's whether the organization is ready to use them. The individual wins are real, and they're stuck at the individual level, waiting on the boring, unglamorous work of turning them into an operating system for the whole company.
>
> That work has names. Standardization, so the best prompt in the building becomes the default, not a personal stash. AI fluency for the entire org, not certification theater, every function knowing how to shape its own work for a model. Skills and workflows as shared assets, with owners and versions. Supervision that scales with autonomy, including the off switch.
>
> The playbook is already inside the building. Your super-users are writing it daily. The work is making it everyone's.

The scorecard that shipped with it:

| Metric | Before | After |
|---|---|---|
| AI-likelihood | 45.7 — suspect | **9.5 — clean** |
| Weighted tells | 6 | 0 |
| Em-dashes / emoji / hashtags | 0 / 1 / 3 | 0 / 0 / 0 |
| Burstiness (target ≥ 0.45) | 0.65 | 0.63 |
| Words | 254 | 235 |

Every number and both report citations survived. Nothing was invented; the
6x moved to the first word, each report got its own statistic, and the
author's best lines ("That work has names," the closing triplet,
"certification theater") came through untouched, because the diagnose pass
had marked them as voice to protect.

We hold this README to the same bar. Its prose scores clean on its own
detector; score the raw file and the number jumps, because the file quotes
the tells it teaches, and a regex cannot tell mention from use. That gap is
the design lesson: the meter flags, judgment decides. Run it yourself with
`python3 scripts/slopscore.py README.md`.

## How it works

The skill runs a five-step loop, and each step exists because a measured
finding says it should.

**Measure.** A two-hundred-line Python script (standard library, no network,
no dependencies) scores the draft: weighted tells across sixty-plus patterns,
sentence-rhythm variance, the overused-word lexicon, formatting noise, and a
followability check that catches prose too dense to absorb.

**Diagnose.** The judgments no regex can make. Which paragraphs say nothing
and would vanish without loss. Which facts must survive verbatim. Which
quirks are the writer's actual voice, and therefore protected.

**Rewrite.** Two passes, because testing showed one combined pass does worse.
First strip the tells. Then build toward an expert register: a practitioner
writing for peers, authority earned by specifics, one idea per sentence, and
the confidence to say the simple true thing.

**Verify.** A hard gate. A LinkedIn post must score 20 or under with zero
em-dashes, zero emoji, zero hashtag clusters. Fail, and the loop iterates.
Fail three times, and it says so instead of pretending.

**Learn.** Every miss becomes a pattern in `data/learned.json`, with a dated
entry in the log. The day this skill shipped, a user caught it attributing
one report's statistic to two reports; that mistake is now a named check
that runs on every future draft.

## The benchmark

We tested Zero-Slop blind against every major alternative: fifty AI-typical
drafts across six genres, scored by independent judges on shuffled labels,
with each skill running its own published prompt verbatim.

| | **Zero-Slop** | blader/humanizer | petergyang/no-ai-slop | isatimur/de-slop |
|---|---|---|---|---|
| Judge composite (1–10) | **8.01** | 7.82 | 6.96 | 6.35 |
| Human-likeness | **7.84** | 7.60 | 6.30 | 5.00 |
| "Which would you publish?" wins | **32/50** | 18/50 | 0 | 0 |
| Detector score after rewrite (drafts start at 76) | **10.9** | 18.7 | 19.4 | 39.7 |

The most useful result was a failure. One Zero-Slop rewrite of a post about
an AWS exam added the phrase "by test day the real thing felt familiar," an
experience the author never described. A blind judge caught it and marked
that rewrite worst on the spot. The fabrication became a hard rule the same
day: invented feelings count as invented facts. A benchmark that can embarrass
its own author is the only kind worth publishing, so the methodology and a
later round against two additional peer skills ship in the repo, reproducible, with the
close results labeled as close.

## What it refuses to do

The fastest way to humanize text is to invent a personal anecdote, which is
why most tools drift there. Zero-Slop treats that as the cardinal sin. No
fake numbers, names, or war stories. No padding a pointless paragraph into
confident emptiness; it gets flagged instead. No trading the AI voice for
performed candor and forced hot takes, the louder dialect of the same
disease. And no detector-evasion for deception: where disclosure is
required, disclose.

## Trust, verifiable

Read [SECURITY.md](SECURITY.md), then read the scorer. Standard library
only. Zero network calls. Your drafts never leave your machine, and personal
voice profiles are git-ignored so they cannot ship by accident. An
enterprise security review of this repo takes about one coffee.

## Install

**Fastest (any agent, macOS/Linux/Windows):** the cross-agent skills CLI
installs into whichever harnesses you use.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Target every supported harness at once with `--agent '*'`, a single one with
`--agent claude-code` (or `codex`, `cursor`, `opencode`, `warp`), or drop
`--global` for a project-local install your team can commit. Update later
with `npx skills update zero-slop --global`.

**Claude Code (plugin system):**

```
/plugin marketplace add manavmishra/ZeroSlop
/plugin install zero-slop@zero-slop
```

**claude.ai and Claude Desktop:** download the repo zip from GitHub and
upload it under Settings → Capabilities → Skills.

**Codex and OpenAI-compatible agents:** install via the skills CLI above, or
point the harness at the repo — `.codex-plugin/plugin.json`,
`agents/openai.yaml`, and `AGENTS.md` ship in the package.

**Cursor, OpenCode, Warp, and other Agent-Skills harnesses:** the skills CLI
handles each via `--agent`, or clone manually into the harness's skills
directory:

```bash
git clone https://github.com/manavmishra/ZeroSlop.git ~/.claude/skills/zero-slop
```

(Windows PowerShell: clone into `$env:USERPROFILE\.claude\skills\zero-slop`;
the folder must be named `zero-slop`.)

**Requirements:** none. The package follows the
[Agent Skills standard](https://agentskills.io) and is plain Markdown plus
one standard-library Python script. The scorer runs on any Python 3.8+
(`python3` on macOS/Linux, `py -3` on Windows); when Python is missing the
skill falls back to its reference lists instead of failing.

Then say: "de-slop this," "humanize this draft," "make this post not sound
like AI," or "score this" for a report without a rewrite.

## The scorer, standalone

```bash
pbpaste | python3 scripts/slopscore.py --explain   # score your clipboard (macOS)
python3 scripts/slopscore.py --json draft.md        # machine-readable
python3 scripts/slopscore.py --formal abstract.txt  # research register
python3 scripts/slopscore.py --predict draft.md     # + trained ML channel
```

Every hit comes back as a quote with a pattern name and a weight. Raw LLM
drafts average around 76. Strong human writing lands between 9 and 29.

## Questions people actually ask

**Is this an AI detector bypass?** No. Detectors flag a writing style;
Zero-Slop removes the style by making the writing better. If your context
requires AI disclosure, disclose.

**Why does ChatGPT say "delve" so much?** The best available answer:
preference tuning. Human raters rewarded a polished formal register, and the
vocabulary came with it. The lexicon also moves; "delve" peaked in 2024, and
newer models lean on "enhance" and "showcase," which is why this skill's
pattern database is versioned and community-updated rather than frozen.

**Are em-dashes really a tell?** Density is. One dash doing real work is
fine almost everywhere except LinkedIn, where readers have decided otherwise.
An early version of this very README used twenty-three of them. The scorer
caught it.

**Will it flatten my voice?** A sample of your real writing outranks every
rule in the skill. If dashes and "honestly" are how you write, they stay.

**Found a tell it missed?** Open a PR adding a regex to `data/learned.json`
and a line to the log. That is the entire contribution process. The taxonomy
is community property.

## Credits

Zero-Slop is a synthesis, and stands on prior work it gratefully credits:
[petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop), and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), all MIT;
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
the field guide that volunteer editors built the hard way; Paul Graham's
writing essays; and the detection literature (Kobak, Liang, Juzek & Ward,
DetectGPT, Binoculars, GPT-who, RAID, DIPPER, Reinhart, Herbold, and others)
cited in [references/evidence.md](references/evidence.md).

## License

[MIT](LICENSE). Take it, fork it, ship it. Keep the credits.
