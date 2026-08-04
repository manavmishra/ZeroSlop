# Zero Slop

**Add taste to your output, or fix your slop.** Zero Slop is a linter for the AI
accent: it scores a draft from 0 to 100, shows you which words cost what, rewrites
it, and proves the rewrite kept your facts and invented nothing.

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-1B1D22">
  <img alt="tests" src="https://img.shields.io/badge/tests-62%20passing-1E7A4C">
  <img alt="dependencies" src="https://img.shields.io/badge/dependencies-0-1E7A4C">
  <img alt="offline" src="https://img.shields.io/badge/network-none-1E7A4C">
  <img alt="version" src="https://img.shields.io/badge/version-1.6.0-2a78d6">
</p>

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

```bash
npx skills add manavmishra/ZeroSlop --global   # then say "de-slop this" in any agent
```

It is not a detector. It will not tell you whether a machine wrote something. It
tells you whether a reader will *think* one did, which is a different question, and
it is the only one a writer can act on. Offline, no account, one standard-library Python
file. It is also still wrong about some things, and those live under
[limitations](#limitations) and [todo](#todo).

## quickstart

```bash
python3 scripts/slopscore.py --explain draft.md          # score it, see every charged span
python3 scripts/slopscore.py --gate 25 draft.md          # exit 1 on failure, for CI
python3 scripts/slopscore.py --fidelity draft.md new.md  # did the rewrite drop or invent a fact?
python3 scripts/slopscore.py --voice you draft.md        # score against your own profile
```

The picture above is real output. Six spans carry the whole score, each one names
itself, and striking them leaves the one fact that was doing any work, the 40%.
That is what the AI accent almost always turns out to be once you read a draft
span by span, decoration wrapped around a single measurement.

## what you get

- **A number you can argue with.** 0 to 100, computed not judged, so it goes in
  CI and every point traces back to a span you can read.
- **Four channels, three of them blind to wording.** A synonym swap does not move
  the score, because only one of the four looks at specific words.
- **A two-pass rewrite.** Strip the tells, then rebuild toward an expert register,
  in that order because benchmarking said so.
- **A fidelity check.** It fails a rewrite that drops one of your figures, names,
  quotes or links, or that adds one you never wrote.
- **It learns from your edits, and adapts to your voice.** What you cut after it
  hands the draft back becomes a new pattern; a sample of your writing quiets the
  words you actually use.
- **Six platform modules** — LinkedIn, X, email, blog, newsletter, research — each
  with its own rules, because a journal abstract and a LinkedIn post fail
  differently.
- **No dependencies, no network, no account.** One stdlib file does the scoring,
  and nothing leaves your machine.

## how it works

Four channels run on every draft, and three of them never look at specific words,
which is why a score holds up when someone swaps synonyms to slip past a word list.

| channel | measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence-length variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

The four fuse into one number, cautiously, because a single stylistic habit is not
evidence. An em-dash or a formal register describes a great deal of excellent human
writing, so those only carry weight once the lexical channel backs them up. Clusters
convict, singles do not. Getting the arithmetic of that rule wrong is the largest way
a detector like this fails, which is exactly what happened here once. The
[limitations](#limitations) tell that story.

<details>
<summary>riders, and the two-pass rewrite</summary>

Riders keep the pattern meter precise instead of trigger-happy. A word like
*leverage* or *robust* or *elevated* is ordinary technical vocabulary until a
marketing trigger lands in the same sentence, so those words live in their own list
and score nothing on their own. "Elevated write volume" in a runbook stays silent;
"elevate your brand with our seamless platform" does.

The rewrite runs in two passes rather than one. The first strips the tells and
touches nothing else. The second rebuilds toward an expert register on the cleaned
text, where the tells are already gone and can no longer hide a weak claim.
Benchmarking settled on that order, since strip-then-build beat a single
do-everything rewrite every time. Each pass only has to hold one idea.

A rewrite is not allowed to invent things, and `--fidelity` is what enforces it. It
inventories the figures, names, quotes, links and stated feelings in your source and
exits non-zero if any went missing, or if any appeared that was not there before.
The second half is the one that matters. A dropped number is something you would
notice; an invented one is not.

The loop also learns. What you strike before publishing was a tell the meter missed,
so `learn.py --reflect` records it, and a span becomes a pattern once three separate
documents have cut it. The loop runs the other way too, dropping the weight of a
pattern you overrule, and `learn.py --voice` builds a profile from your own writing
so the meter stops charging you for the words you reach for by habit.

</details>

## benchmarks

Fifty AI-typical drafts across six genres, judged blind on shuffled labels. Read
this as a design study rather than a head-to-head: the competitor outputs in
`bench/outputs/` were written to represent each tool's published prompt rather than
produced by running it, only Zero Slop's rewrites iterated against a gate, and the
judge prompts were never recorded.

The first run gave Zero Slop 32 of 50 best-picks; a replication with fresh judges on
the identical rewrites gave 23. Cohen's kappa came out at 0.12, so the judges barely
agree on "best" and any single run is mostly noise. The number worth quoting is the
pool of all 100 verdicts:

| method | best-picks | composite r1 | composite r2 |
|---|--:|--:|--:|
| Zero Slop | 55 | 8.01 | 7.51 |
| blader/humanizer | 40 | 7.82 | 7.51 |
| petergyang/no-ai-slop | 5 | 6.96 | 6.87 |
| isatimur/de-slop | 0 | 6.35 | 6.60 |

It takes the plurality against a 25% chance rate (p = 1.7e-10, 95% CI [45%, 64%]),
it is not statistically separable from blader/humanizer head to head (p = 0.15), and
both beat the other two decisively (p < 1e-7).

The panel below is steadier because it is computed rather than judged, with one catch:
it is scored by Zero Slop's own detector. Read it as how much of the surface register
each method strips, as measured by the thing that defines the register, not as an
independent verdict.

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

Both Zero Slop rows are here because they are two different builds. v1.0 won the 55
best-picks and did it while cutting drafts 22% shorter; v1.2 holds the original length
and no judge ever saw it, so read that length column as a fact about v1.2, not a judged
result.

A separate test asks a simpler question: can the meter tell obvious slop from obvious
human writing across LinkedIn, blog, social, Reddit and newsletter? It separates the
two by 77 points, AUC 1.000, no overlap, with the honest caveat that I wrote both
classes, so it shows the meter agreeing with an obvious judgment rather than
generalising to text in the wild. It runs in `bench/discrimination/`, and the whole
thing scores about 1,100 documents a second.

## limitations

The most useful thing the benchmark told me was where the skill fell down. It came
last of four on fidelity, 8.80 against 9.32, 9.58 and 9.66, and was the only tool
in the run to earn a fabrication flag, for a rewrite that handed the author a feeling
they had never claimed. That one stings most, because not inventing things is the
first rule the skill sets for itself. The cause was structural. The gate measured
vocabulary, rhythm, format and register, and nothing measured whether the facts
survived. That is what `--fidelity` now repairs, though a claim quietly reframed still slips
past it, and I would rather say so than imply otherwise.

A word on the number itself, because it misleads people. 9.5 is the floor, not a grade. A document with nothing charged scores 9.5, and so does the bare string
`Hello`, so the span list is what you actually read and the composite is only the
summary under it. For scale, the fifty raw AI drafts in `bench/` average around 70,
and the human writing in `data/corpus/` lands between 9 and 21.

The accuracy figures need the same honesty, because the ground under them is thin, and
every one of them comes from corpora I wrote. Early on the scorer convicted five of the eight
human documents in its own repository, from two arithmetic bugs in the corroboration
rule that were letting style carry a verdict with no lexical evidence behind it. Both
are fixed, both are under test, and the rate on ordinary prose is down to zero of five,
but five documents is a direction, not a rate. A false-positive figure anyone should
trust needs on the order of a thousand labelled human samples, and that corpus does not
exist here yet. It is first on the todo list, and not by accident.

Underneath all of it sit the regexes, which are brittle by their nature. Every false
positive I have traced came from a pattern firing on legitimate notation, and every
miss from phrasing nothing anticipated. Three of the four channels already ignore
specific wording, and the durable answer is more channels of that kind rather than more
patterns. It is also why a README about slop scores high on its own meter: it is built
out of the exact words slop is made of, and no regex tells a specimen apart from an
assertion.

## todo

- **A labelled corpus at volume.** The blocker for every quantitative claim in the
  repo. RAID, HC3, M4 and AuTextification are free, labelled, and cover email, social
  and blog. Tuning before it exists is how the five-in-eight false-positive rate went
  unnoticed until someone measured it.
- **Stylometric channels that use no patterns.** Current research (NEULIF,
  [arXiv:2511.21744](https://arxiv.org/abs/2511.21744)) puts function-word bigram
  frequency and sentence-length distribution at the top of the interpretable-feature
  list. They ignore wording, so a synonym swap cannot dodge them. On the twelve-sample
  corpus they show no signal, which is proof the corpus is too small to calibrate them,
  and one more reason the labelled corpus comes first.
- **Actually run the competitors.** The comparison is not a real head-to-head until
  each tool is executed and logged.
- **Fidelity that reads claims, not just entities.** It catches an invented name; it
  still misses a reframed argument.

## why this matters now

Four platforms shipped countermeasures within two weeks of each other, across late
July and early August 2026. LinkedIn added a reader-facing "seems like AI slop" report,
and flagged posts now lose reach beyond the author's own network. Snapchat pulled
wholly AI-generated video out of Spotlight. YouTube made generic and template-based
video ineligible for monetisation. Substack shipped a reader-facing detector, citing
research that up to 40% of social-media writing is now synthetic.

Every one of them drew the same line: AI that refines your work is fine, AI that
produces it is not. This tool sits on the right side of that line by construction,
because it never writes a draft, it only measures and rewrites yours. The upshot is
that reach now depends on whether readers believe a machine wrote it, which quietly
turns the AI accent from a question of taste into a question of distribution.

## repository

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
suite covers the detector, the learning gates, decay and throughput, plus guards that
exist because each of these drifted once: documented counts have to match the data,
calibration anchors have to match the corpora, the plugin mirror and bundle have to be
current, and no user prose is allowed to reach a git-tracked file.

## acknowledgements

Builds on [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop) and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), all MIT;
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
and Kagi's [SlopStop](https://help.kagi.com/kagi/features/slopstop.html), which arrived
independently at the same two ideas this tool leans on, corroboration before conviction
and a first-class appeals path. The thirteen detection papers behind the design are
cited in [references/evidence.md](references/evidence.md); the load-bearing ones are the
post-training register finding (arXiv:2605.19516), the excess-vocabulary method (Kobak
et al., arXiv:2406.07016), and Liang et al. (arXiv:2304.02819), which found that
detectors misclassify over half of non-native English writing and is the reason a
non-native sample sits in the safety corpus.

MIT.
