# Zero Slop

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-1B1D22">
  <img alt="tests" src="https://img.shields.io/badge/tests-62%20passing-1E7A4C">
  <img alt="dependencies" src="https://img.shields.io/badge/dependencies-0-1E7A4C">
  <img alt="offline" src="https://img.shields.io/badge/network-none-1E7A4C">
  <img alt="version" src="https://img.shields.io/badge/version-1.6.0-2a78d6">
</p>

Zero Slop is a linter for the AI accent. It scores a draft from 0 to 100, shows
which words cost what, rewrites it, and proves the rewrite kept every fact and
invented nothing.

It gives writers and agents a measurable way to catch the phrasing that reads as
machine-written, remove it, and show the before and after as numbers rather than
opinion.

Use it when writing goes out under your name and needs to read as yours: a
LinkedIn post, an article, a newsletter, an email, a research abstract, or any
prose an agent generated that you are about to present as your own.

```text
Draft -> Measure -> Diagnose -> Rewrite -> Verify -> Learn
         0-100       claims      strip/build  gate      your edits
```

Zero Slop is a de-slopper, not a writer. It subtracts the tells and returns your
words, your structure, and your voice intact. A draft that already reads human
comes back unchanged.

It is not a detector. It does not decide whether a machine wrote something. It
tells you whether a reader will think one did, which is a different question and
the only one a writer can act on.

Design principle: measure the parts that can be removed without changing meaning,
and leave the meaning alone.

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

## What It Does

- Scores any draft 0 to 100, computed rather than judged, so the number goes in
  CI and every point traces back to a span you can read.
- Names the exact spans that cost the score, each with a weight and a plain fix.
- Rewrites in two passes: strip the tells, then rebuild toward an expert register.
- Checks its own rewrite against the source and fails it for a dropped or invented
  fact.
- Learns from the edits you make after it hands the draft back, and adapts to the
  words you use by habit.
- Runs six platform modules, for LinkedIn, X, email, blog, newsletter and
  research, because a journal abstract and a LinkedIn post fail differently.

## What It Does Not Do

- It does not classify authorship, sell to schools or compliance teams, or
  optimise against detector scores. The people who would want that defeated are
  the ones it refuses to serve.
- It does not judge whether an idea is worth stating. A clean score on hollow
  content is still hollow, and the report says so.
- It does not invent. No fabricated numbers, names, anecdotes or feelings, and
  where disclosure is required, it discloses.

## Quick Start

```bash
npx skills add manavmishra/ZeroSlop --global   # then say "de-slop this" in any agent
```

From the command line:

```bash
python3 scripts/slopscore.py --explain draft.md          # score it, see every charged span
python3 scripts/slopscore.py --gate 25 draft.md          # exit 1 on failure, for CI
python3 scripts/slopscore.py --fidelity draft.md new.md  # did the rewrite drop or invent a fact?
python3 scripts/slopscore.py --voice you draft.md        # score against your own profile
```

The image above is real output. Six spans carry the whole score, each one names
itself, and striking them leaves the one fact that was doing any work, the 40%.
That is what the AI accent almost always turns out to be once a draft is read span
by span: decoration wrapped around a single measurement. Requirements are none.
One standard-library Python file does the scoring, and nothing leaves the machine.

## How It Works

Four channels run on every draft. Three of them never look at specific words, so
a synonym swap does not move the score.

| channel | measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence-length variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

The four fuse into one number, cautiously, because a single stylistic habit is not
evidence. An em-dash or a formal register describes a great deal of excellent human
writing, so those carry weight only once the lexical channel agrees. Clusters
convict, singles do not.

Riders keep the pattern meter precise. A word like *leverage* or *robust* or
*elevated* is ordinary technical vocabulary until a marketing trigger shares its
sentence, so those words score nothing on their own. "Elevated write volume" in a
runbook stays silent; "elevate your brand with our seamless platform" does not.

## The Checks

Three gates stand behind the rewrite.

The score gate holds the composite under a genre threshold, strictest on LinkedIn.

The fidelity check inventories the figures, names, quotes, links and stated
feelings in the source and exits non-zero if any went missing, or if any appeared
that was not there before. The second half is the one that matters, because a
dropped number is visible to the author and an invented one is not.

The reflect loop turns edits into evidence. What a writer strikes before publishing
was a tell the meter missed, and a span becomes a pattern only after three separate
documents cut it. The loop runs the other way too, lowering the weight of a pattern
writers overrule. A voice profile, built from a sample of one author's writing,
quiets the words that author uses by habit without touching anyone else's meter.

## Benchmarks

Fifty AI-typical drafts across six genres, judged blind on shuffled labels. This is
a design study, not a head-to-head: the competitor outputs in `bench/outputs/` were
written to represent each tool's published prompt rather than produced by running
it, only Zero Slop's rewrites iterated against a gate, and the judge prompts were
not recorded.

The first run gave Zero Slop 32 of 50 best-picks; a replication with fresh judges on
the identical rewrites gave 23. Cohen's kappa was 0.12, so the judges barely agree
on "best" and any single run is noise. Pooled across 100 verdicts:

| method | best-picks | composite r1 | composite r2 |
|---|--:|--:|--:|
| Zero Slop | 55 | 8.01 | 7.51 |
| blader/humanizer | 40 | 7.82 | 7.51 |
| petergyang/no-ai-slop | 5 | 6.96 | 6.87 |
| isatimur/de-slop | 0 | 6.35 | 6.60 |

It takes the plurality against a 25% chance rate (p = 1.7e-10, 95% CI [45%, 64%]),
it is not statistically separable from blader/humanizer head to head (p = 0.15),
and both beat the other two decisively (p < 1e-7).

The panel below is steadier because it is computed rather than judged, with one
caveat: it is scored by Zero Slop's own detector. Read it as how much of the surface
register each method strips, not as an independent verdict.

| method | detector | followability | words |
|---|--:|--:|--:|
| original drafts | 69.0 | 0.46 | 159 |
| isatimur/de-slop | 23.4 | 0.41 | 137 |
| stacked pipeline | 21.2 | 0.38 | 114 |
| blader/humanizer | 19.3 | 0.46 | 135 |
| petergyang/no-ai-slop | 18.7 | 0.41 | 123 |
| hardikpandya/stop-slop | 15.7 | 0.33 | 116 |
| Zero Slop v1.0 (judged) | 10.4 | 0.36 | 128 |
| Zero Slop v1.2 | 9.8 | 0.07 | 159 |

Both Zero Slop rows are here because they are two builds. v1.0 won the 55 best-picks
and cut drafts 22% shorter; v1.2 holds the original length and no judge saw it, so
read that length column as a fact about v1.2, not a judged result.

A separate test asks whether the meter can tell obvious slop from obvious human
writing across LinkedIn, blog, social, Reddit and newsletter. It separates the two
by 77 points, AUC 1.000, no overlap, with the caveat that both classes were authored
for the corpus, so it shows the meter agreeing with an obvious judgment rather than
generalising. It runs in `bench/discrimination/`, and the whole thing scores about
1,100 documents a second.

## Limitations

The benchmark's most useful result was the one that went against the tool. Zero Slop
came last of four on fidelity, 8.80 against 9.32, 9.58 and 9.66, and it was the only
tool to earn a fabrication flag, for a rewrite that gave the author a feeling they
never described. The gate measured vocabulary, rhythm, format and register, and
nothing measured whether the facts survived. `--fidelity` repairs that now, though a
claim quietly reframed still slips past it.

9.5 is the floor, not a grade. A document with nothing charged scores 9.5, and so
does the string `Hello`, so the span list is the reading and the composite is the
summary. For scale, the raw AI drafts in `bench/` average around 70 and the human
writing in `data/corpus/` lands between 9 and 21.

The accuracy figures rest on corpora authored for this repo. The scorer once
convicted five of the eight human documents it ships with, from two arithmetic bugs
in the corroboration rule; both are fixed and under test, and the rate on ordinary
prose is now zero of five. Five documents is a direction, not a rate. A trustworthy
false-positive figure needs on the order of a thousand labelled human samples, and
that corpus does not exist yet.

Regexes are brittle by nature. Every false positive traces to a pattern firing on
legitimate notation, and every miss to phrasing nothing anticipated. Three of the
four channels already ignore specific wording, and the durable answer is more
channels of that kind, not more patterns.

## Roadmap

- A labelled corpus at volume. It is the blocker for every quantitative claim.
  RAID, HC3, M4 and AuTextification are free, labelled, and cover email, social and
  blog.
- Stylometric channels that use no patterns. Current research (NEULIF,
  [arXiv:2511.21744](https://arxiv.org/abs/2511.21744)) puts function-word bigram
  frequency and sentence-length distribution at the top of the interpretable-feature
  list. They ignore wording, so a synonym swap cannot dodge them, and they wait on
  the corpus above for calibration.
- A real head-to-head. The comparison is a design study until each competitor is
  executed and logged.
- Fidelity that reads claims, not just entities. It catches an invented name; it
  misses a reframed argument.

## Why This Matters Now

Four platforms shipped countermeasures within two weeks of each other, across late
July and early August 2026. LinkedIn added a reader-facing "seems like AI slop"
report, and flagged posts lose reach beyond the author's own network. Snapchat
pulled wholly AI-generated video from Spotlight. YouTube made generic and
template-based video ineligible for monetisation. Substack shipped a reader-facing
detector, citing research that up to 40% of social-media writing is now synthetic.

Each of them drew the same line: AI that refines your work is fine, AI that produces
it is not. Zero Slop sits on the refining side by construction, because it never
writes a draft, it measures and rewrites yours. Reach now depends on whether readers
believe a machine wrote it, which turns the AI accent from a question of taste into a
question of distribution.

## Repository

```
SKILL.md                    the runtime artifact: the loop the agent follows
scripts/slopscore.py        the scorer, stdlib only
scripts/learn.py            the reflect loop and voice profiles
scripts/calibrate.py        refit weights from a corpus; decay stale tells
data/patterns.json          74 weighted patterns, lexicon, riders
data/corpus/must-not-flag/  writing that must never be flagged
references/                 taxonomy, rewrite moves, platform modules, evidence
bench/                      the benchmark harness and the discrimination test
tests/test_all.py           62 tests
```

Run `python3 tests/test_all.py` and `python3 scripts/calibrate.py --selftest`. The
suite covers the detector, the learning gates, decay and throughput, plus guards
that exist because each of these drifted once: documented counts match the data,
calibration anchors match the corpora, the plugin mirror and bundle stay current,
and no user prose reaches a git-tracked file.

## Acknowledgements

Builds on [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop) and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), all MIT;
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
and Kagi's [SlopStop](https://help.kagi.com/kagi/features/slopstop.html), which
arrived independently at the same two ideas this tool leans on, corroboration before
conviction and a first-class appeals path. The thirteen detection papers behind the
design are cited in [references/evidence.md](references/evidence.md); the load-bearing
ones are the post-training register finding (arXiv:2605.19516), the excess-vocabulary
method (Kobak et al., arXiv:2406.07016), and Liang et al. (arXiv:2304.02819), which
found that detectors misclassify over half of non-native English writing and is the
reason a non-native sample sits in the safety corpus.

MIT.
