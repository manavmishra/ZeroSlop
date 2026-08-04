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
invented nothing. The score is computed, not judged, so you can put it in CI and
trace every point back to a span you can read.

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

That is real output, not a mockup. Six spans carry the entire score, each one
names itself, and cutting them leaves the only fact that was doing any work: the
40%. Read almost any AI draft span by span and you find the same shape,
decoration wrapped around a single measurement.

It is for anyone who does not want AI slop in their writing: a founder posting
under their own name, a comms team shipping on a schedule, a researcher who needs
the formal register left intact, an engineering team that wants slop to fail CI
like any other lint rule. If you use AI to help you write and do not want the
result to read like it, this is for you.

## The Problem

Every large model writes in the same voice. Strip a model's assistant training and
detectors rate its raw output as human 97 to 99 percent of the time, so the tell is
not machine generation, it is the post-training register: phrasing that sits at the
most probable word, uniform sentence rhythm, a few hundred over-used style words,
and relentless even polish. Readers learned to hear it quickly. An em-dash on
LinkedIn now gets a writer accused of outsourcing their thinking.

It became a serious problem the moment platforms started ranking on it. Across two
weeks in late July and early August 2026, four of them shipped countermeasures.
LinkedIn added a reader-facing "seems like AI slop" report, and flagged posts lose
reach beyond the author's own network. Snapchat pulled wholly AI-generated video
from Spotlight. YouTube made generic and template-based video ineligible for
monetisation. Substack shipped a reader-facing detector, citing research that up to
40% of social-media writing is now synthetic. Reach now depends on whether readers
believe a machine wrote your post, which turns the AI accent from a question of
taste into a question of distribution. Underneath that, the same slop is polluting
the training data of the next models, so removing it is a contribution to the
commons and not only to one post's reach.

## Standing on Prior Work

Zero Slop did not invent de-slopping. It builds directly on four open-source
projects that defined the craft: [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop), and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop). Their prompts
proved the AI accent is removable, and their taxonomies of tells seeded this one.
Zero Slop's patterns, lexicon, and rewrite ladder all start from that work, and the
benchmark below runs against their published prompts out of respect for what they
got right.

What Zero Slop adds is measurement. Those tools are prompts: you paste a draft and
get one back, which is often exactly what a writer wants. Zero Slop takes the same
idea and puts a number on it, so the change is visible, gate-able and checkable, and
it adds two guarantees a prompt cannot make on its own: that your facts survive the
rewrite, and that the meter gets better the more you use it.

Detectors are a separate craft again. Pangram and GPTZero answer "did a machine
write this," which is the right question for a teacher or a compliance team, and they
answer it well. Zero Slop answers a different question for the writer, and it does not
compete with them or optimise against their scores.

## What Zero Slop Adds

Building on that foundation, four things make it more than a prompt.

**A number, not an opinion.** The score comes from interpretable channels rather than
a trained model, so every point traces to a span you can read and the number goes in
CI. It also degrades gracefully: when models change you edit a data file and watch the
diff, where a trained detector quietly drifts.

**Your facts, guaranteed.** `--fidelity` inventories your figures, names, quotes and
stated feelings and fails a rewrite that drops one or invents one. This is the failure
the benchmark caught the tool committing before the check existed, and building the
guarantee in is the point.

**Your voice, preserved.** It is a de-slopper, not a writer. It removes the tells and
returns your words, structure and voice, and a draft that already reads human comes
back unchanged.

**A meter that learns.** What you cut after it hands the draft back becomes a new
pattern once three documents agree; a pattern you overrule loses weight; and a profile
built from your own writing quiets the words you use by habit. The meter sharpens with
use instead of ageing out. See [Self-Learning](#self-learning) below.

And it is honest about its limits: the sections below publish the dimension the tool
lost on, its false-positive history, and the fact that its accuracy numbers rest on
corpora authored for this repo.

## Quick Start

```bash
npx skills add manavmishra/ZeroSlop --global   # then say "de-slop this" in any agent
```

`--agent '*'` installs to every harness; name one (`claude-code`, `codex`,
`cursor`, `opencode`, `warp`, `zed`) to scope it; drop `--global` for a
project-local install.

<details>
<summary>Claude Code plugin · ChatGPT · Codex · claude.ai · manual clone</summary>

Claude Code and Cowork, as a plugin:

```
/plugin marketplace add manavmishra/ZeroSlop
/plugin install zero-slop@zero-slop
```

ChatGPT and ChatGPT at Work: paste the single-file bundle into a Project's
instructions, or upload it as Custom GPT knowledge.

```bash
curl -sLO https://raw.githubusercontent.com/manavmishra/ZeroSlop/main/dist/zero-slop-single-file.md
```

Codex: run this in your own project, not a clone of this repo, since it writes
`AGENTS.md`.

```bash
curl -sL https://raw.githubusercontent.com/manavmishra/ZeroSlop/main/dist/zero-slop-single-file.md -o AGENTS.md
```

claude.ai and Desktop: download the repo zip and upload it under Settings,
Capabilities, Skills.

Manual, any tool:

```bash
git clone https://github.com/manavmishra/ZeroSlop.git ~/.claude/skills/zero-slop
```

The folder must be named `zero-slop`. On Windows, clone into
`$env:USERPROFILE\.claude\skills\zero-slop`.

</details>

From the command line:

```bash
python3 scripts/slopscore.py --explain draft.md          # score it, see every charged span
python3 scripts/slopscore.py --gate 25 draft.md          # exit 1 on failure, for CI
python3 scripts/slopscore.py --fidelity draft.md new.md  # did the rewrite drop or invent a fact?
python3 scripts/slopscore.py --voice you draft.md        # score against your own profile
```

Requirements are none. One standard-library Python file does the scoring, nothing
leaves the machine, and where Python is unavailable the skill falls back to its
reference lists, losing the numeric gate but not the rewrite.

Every draft goes through the same loop, and the sections below walk it in order.

```text
Draft -> Measure -> Diagnose -> Rewrite -> Verify -> Learn
         0-100       claims      strip/build  gate      your edits
```

Design principle: measure the parts that can be removed without changing meaning,
and leave the meaning alone.

## How It Works

The **Measure** stage runs four channels on every draft. Three of them never look at
specific words, so a synonym swap does not move the score.

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

Riders are what keep the pattern meter precise. A word like *leverage* or *robust*
or *elevated* is ordinary technical vocabulary until a marketing trigger shares its
sentence, so those words score nothing on their own. "Elevated write volume" in a
runbook stays silent; "elevate your brand with our seamless platform" does not.

**Diagnose** and **Rewrite** follow. Diagnose reads what the meter cannot: whether a
paragraph makes a claim at all, which facts must survive, and what in the draft is
the author's voice. The rewrite then runs in two passes, because benchmarking
showed strip-then-build beats a single do-everything pass. The first pass strips the
tells and touches nothing else; the second rebuilds toward an expert register on the
cleaned text, where the tells are already gone and can no longer hide a weak claim.

## The Checks

Three gates stand at **Verify**, and the third feeds **Learn**.

The score gate holds the composite under a genre threshold, strictest on LinkedIn.

The fidelity check inventories the figures, names, quotes, links and stated feelings
in the source and exits non-zero if any went missing, or if any appeared that was not
there before. The second half is the one that matters, because a dropped number is
visible to the author and an invented one is not.

The reflect loop turns edits into evidence. What a writer strikes before publishing
was a tell the meter missed, and a span becomes a pattern only after three separate
documents cut it. The loop runs the other way too, lowering the weight of a pattern
writers overrule. A voice profile, built from a sample of one author's writing,
quiets the words that author uses by habit without touching anyone else's meter.

## Self-Learning

The meter is not frozen at what its authors happened to notice. It improves along two
tracks.

The data improves from real edits. Point `learn.py --reflect` at what the skill
produced and what you actually published, and it records the spans you cut. A span
becomes a pattern only after three separate documents cut it, so one person's habit
never poisons the meter, and it must clear the certified-human corpus before it ships.
The loop also runs backward: a pattern writers repeatedly overrule loses half its
weight, and stale tells decay on their own. Verified end to end in the test suite, and
you can watch the curve with `learn.py --stats`.

```bash
python3 scripts/learn.py --reflect --produced out.md --shipped final.md
python3 scripts/learn.py --promote --apply     # mint spans three documents agreed on
python3 scripts/learn.py --voice you --from ~/my-writing/   # a profile that quiets your habits
python3 scripts/learn.py --stats               # taxonomy age, sources, what is pending
```

The instructions can improve too. The scoring loop lives in `SKILL.md`, and the repo
already ships the eval harness that improving it would need: the gate, the
discrimination corpus, and the benchmark. That is exactly the setup Microsoft's
[SkillOpt](https://github.com/microsoft/SkillOpt) optimises against, treating the skill
file as trainable state and gating each edit on a held-out score. Wiring the two
together, so the reflect loop sharpens the data while SkillOpt sharpens the
instructions against the same gate, is on the [roadmap](#roadmap).

## Benchmarks

Fifty AI-typical drafts across six genres, judged blind on shuffled labels. This is a
design study, not a head-to-head: the competitor outputs in `bench/outputs/` were
written to represent each tool's published prompt rather than produced by running it,
only Zero Slop's rewrites iterated against a gate, and the judge prompts were not
recorded.

The first run gave Zero Slop 32 of 50 best-picks; a replication with fresh judges on
the identical rewrites gave 23. Cohen's kappa was 0.12, so the judges barely agree on
"best" and any single run is noise. Pooled across 100 verdicts:

![Best-picks, pooled over 100 blind verdicts: Zero Slop 55, blader 40, no-ai-slop 5, de-slop 0](assets/bench-bestpicks.png)

| method | best-picks | composite r1 | composite r2 |
|---|--:|--:|--:|
| Zero Slop | 55 | 8.01 | 7.51 |
| blader/humanizer | 40 | 7.82 | 7.51 |
| petergyang/no-ai-slop | 5 | 6.96 | 6.87 |
| isatimur/de-slop | 0 | 6.35 | 6.60 |

It takes the plurality against a 25% chance rate (p = 1.7e-10, 95% CI [45%, 64%]), it
is not statistically separable from blader/humanizer head to head (p = 0.15), and both
beat the other two decisively (p < 1e-7).

The panel below is steadier because it is computed rather than judged, with one
caveat: it is scored by Zero Slop's own detector. Read it as how much of the surface
register each method strips, not as an independent verdict.

![AI register remaining after de-slop, detector score lower is cleaner: Zero Slop 9.8 vs 15.7 to 23.4 for others, original drafts 69.0](assets/bench-detector.png)

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
writing across LinkedIn, blog, social, Reddit and newsletter. It separates the two by
77 points, AUC 1.000, no overlap, with the caveat that both classes were authored for
the corpus, so it shows the meter agreeing with an obvious judgment rather than
generalising. It runs in `bench/discrimination/`, and the whole thing scores about
1,100 documents a second.

## Limitations

The benchmark's most useful result was the one that went against the tool. Zero Slop
came last of four on fidelity, 8.80 against 9.32, 9.58 and 9.66, and it was the only
tool to earn a fabrication flag, for a rewrite that gave the author a feeling they
never described. The gate measured vocabulary, rhythm, format and register, and
nothing measured whether the facts survived. `--fidelity` repairs that now, though a
claim quietly reframed still slips past it.

9.5 is the floor, not a grade. A document with nothing charged scores 9.5, and so does
the string `Hello`, so the span list is the reading and the composite is the summary.
For scale, the raw AI drafts in `bench/` average around 70 and the human writing in
`data/corpus/` lands between 9 and 21.

The accuracy figures rest on corpora authored for this repo. The scorer once convicted
five of the eight human documents it ships with, from two arithmetic bugs in the
corroboration rule; both are fixed and under test, and the rate on ordinary prose is
now zero of five. Five documents is a direction, not a rate. A trustworthy
false-positive figure needs on the order of a thousand labelled human samples, and
that corpus does not exist yet.

Regexes are brittle by nature. Every false positive traces to a pattern firing on
legitimate notation, and every miss to phrasing nothing anticipated. Three of the four
channels already ignore specific wording, and the durable answer is more channels of
that kind, not more patterns.

## What It Refuses

It will not invent a number, name, anecdote or feeling. Hollow paragraphs are flagged,
not padded. Performed candor and forced hot takes are turned away as the louder
dialect of the same disease. And it will not defeat a disclosure requirement or
impersonate a named person: where disclosure is required, it discloses.

## Roadmap

- A labelled corpus at volume. It is the blocker for every quantitative claim. RAID,
  HC3, M4 and AuTextification are free, labelled, and cover email, social and blog.
- Stylometric channels that use no patterns. Current research (NEULIF,
  [arXiv:2511.21744](https://arxiv.org/abs/2511.21744)) puts function-word bigram
  frequency and sentence-length distribution at the top of the interpretable-feature
  list. They ignore wording, so a synonym swap cannot dodge them, and they wait on the
  corpus above for calibration.
- A real head-to-head. The comparison is a design study until each competitor is
  executed and logged.
- Fidelity that reads claims, not just entities. It catches an invented name; it
  misses a reframed argument.
- Optimise `SKILL.md` against the gate with Microsoft
  [SkillOpt](https://github.com/microsoft/SkillOpt), so the rewrite instructions
  improve on a held-out score the way the data already improves from edits.

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
suite covers the detector, the learning gates, decay and throughput, plus guards that
exist because each of these drifted once: documented counts match the data,
calibration anchors match the corpora, the plugin mirror and bundle stay current, and
no user prose reaches a git-tracked file.

## Acknowledgements

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
