# Zero Slop

A linter for the AI accent. It scores a draft from 0 to 100, shows you which
spans cost what, rewrites it, and checks that the rewrite kept your facts and
invented nothing. The score is computed rather than judged, which is the whole
point: you can gate CI on it, diff it across revisions, and argue with any number
it gives you, because each one traces back to something you can read.

It is not a detector, and it will not tell you whether a machine wrote something.
It tells you whether a reader will *think* one did, which is a different question
and the only one a writer can act on.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then say "de-slop this" in any agent. There are no dependencies, no network calls
and no account: a single standard-library Python file does the scoring, and
nothing leaves your machine. It is also still wrong about some things, and those
are collected honestly under [limitations](#limitations) and [todo](#todo).

## how it reads a draft

Start with a sentence a product marketer would call finished:

> We're thrilled to announce that our team has leveraged cutting-edge AI to deliver a seamless onboarding experience, reducing setup time by 40%.

```console
$ python3 scripts/slopscore.py --explain draft.md
AI-likelihood: 100.0/100  [slop]
  tell density : 38.33 weighted hits /100w (22 words)

  charged spans (6), heaviest first:
       5  linkedin       announce-excited       "We're thrilled to"
       4  marketing      marketing-register     'cutting-edge'
       4  marketing      marketing-register     'seamless'
       4  lexicon        cutting-edge           'cutting-edge'
       4  lexicon        seamless               'seamless'
       2  rider          leverage               'leveraged'
                                                = 23 weighted, 38.33 per 100 words
```

Six spans carry the whole score, and each one names itself. `seamless` is charged
twice on purpose, once as marketing register and once as vocabulary, because two
channels agreeing is stronger evidence than either alone. `leveraged` scores only
2, because it is a *rider*: it would stay silent in "we leveraged the existing
index", and it fires here only because marketing words share its sentence. That
single idea is what the rest of the scorer is built on.

Now strike the six spans, and one fact is left standing:

> We cut onboarding setup time by 40% using AI.

```console
$ python3 scripts/slopscore.py --explain rewrite.md
AI-likelihood: 9.5/100  [clean]
  tell density : 0.00 weighted hits /100w (8 words)

  charged spans: none — the score is rhythm and format only
```

Twenty-two words became eight, and the one survivor is the 40%. That ratio is the
argument for the whole tool. Most of the original was decoration wrapped around a
single measurement, and once you read a draft span by span, that is what the AI
accent almost always turns out to be.

## how it works

Four channels run on every draft, and three of them never look at specific words
at all. That is deliberate, and it is why a score holds up even when someone
swaps synonyms to dodge a word list.

| channel | measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence-length variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

The four fuse into one number, and the fusion is cautious on purpose, because a
single stylistic habit is not evidence of anything. An em-dash or a formal
register describes a great deal of excellent human writing, so those only carry
weight once the lexical channel backs them up. Clusters convict; singles do not.
Getting the arithmetic of that rule wrong is the largest way a detector like this
fails, which is exactly what happened here at one point — the story is under
[limitations](#limitations).

Riders are the trick that keeps the pattern meter precise instead of
trigger-happy. A word like *leverage* or *robust* or *elevated* is ordinary
technical vocabulary right up until a marketing trigger lands in the same
sentence, so those words live in their own list and score nothing on their own.
"Elevated write volume" in a runbook stays silent; "elevate your brand with our
seamless platform" does not.

Scoring is only half of it. The rewrite runs in two passes rather than one: the
first strips the tells and touches nothing else, and the second rebuilds toward an
expert register on the cleaned-up text, where the tells are already gone and can
no longer hide a weak claim. Benchmarking is what settled on that order, because a
strip-then-build sequence beat a single do-everything rewrite every time. Each
pass only has to hold one idea in its head.

## it verifies its own rewrite

A rewrite is not allowed to invent things, and for a long time that was just a
rule the agent was asked to follow. Asking turned out not to be enough — in the
benchmark below, it was the one dimension the skill lost on. So now it is checked:

```bash
python3 scripts/slopscore.py --fidelity original.md rewrite.md
```

The check inventories the figures, names, quotes, links and stated feelings in
your source, then exits non-zero if any of them went missing, or if any appeared
that was not there before. The second half is the one that matters, because a
dropped number is something you would notice yourself, while an invented one is
not, and inventing is precisely what the benchmark caught the skill doing. It
cannot see a claim that has been quietly reframed, so the judgment pass still
covers those, and every run says as much out loud.

## it learns from your edits, and adapts to you

The most honest signal a linter can get is what you change *after* it hands the
draft back. If you strike a phrase before publishing, that phrase was a tell the
meter missed, in your genre, in your voice, from the model generation
you actually write against.

```bash
python3 scripts/learn.py --reflect --produced out.md --shipped final.md
python3 scripts/learn.py --promote --apply
```

One edit on its own changes nothing. A span only becomes a pattern after three
separate documents have cut it, because a single diff cannot tell a real tell
from an author trimming a sentence for length. An early version watched one writer
delete "the people is the standard we hold ourselves to" and flagged it as a
tell; it was not one, it was just content. The loop runs the other way too: a
pattern you overrule three times loses half its weight, because a meter that can
only grow eventually flags everything.

It also learns *you*, specifically. Build a profile once from a sample of your own
writing, and the meter stops charging you for the tell-words you actually use,
while everyone else's meter stays exactly as it was and real slop still gets
caught:

```bash
python3 scripts/learn.py --voice you --from ~/my-writing/
python3 scripts/slopscore.py --voice you draft.md
```

A sample of how you actually write outranks every global rule in the tool, on the
theory that a linter you can teach is worth more than one you spend your time
fighting. All of this reflection data lives in `~/.zero-slop/`, never in the
repository, and it is built from your own drafts. Sharing what it learned upstream
is a single opt-in command that prints the entire payload first — spans and
counts, never your source text — before it writes a thing.

## benchmarks

Fifty AI-typical drafts across six genres, judged blind on shuffled labels. Read
what follows as a design study rather than a head-to-head, and here is why: the
competitor outputs in `bench/outputs/` were written to represent each tool's
published prompt rather than produced by running it, only Zero Slop's rewrites
iterated against a gate, and the judge prompts and model ids were never recorded.

The first run gave Zero Slop 32 of 50 best-picks. A replication with fresh judges
on the identical rewrites gave 23. Cohen's kappa came out at 0.12, meaning the
judges barely agree on "best" and any single run is mostly noise, so the number
worth quoting is the pool of all 100 verdicts:

| method | best-picks | composite r1 | composite r2 |
|---|--:|--:|--:|
| Zero Slop | 55 | 8.01 | 7.51 |
| blader/humanizer | 40 | 7.82 | 7.51 |
| petergyang/no-ai-slop | 5 | 6.96 | 6.87 |
| isatimur/de-slop | 0 | 6.35 | 6.60 |

It takes the plurality against a 25% chance rate (p = 1.7e-10, 95% CI [45%, 64%]),
it is not statistically separable from blader/humanizer head to head (p = 0.15),
and both of them beat the other two decisively (p < 1e-7).

The panel below is steadier, because it is computed rather than judged, but there
is a catch worth stating before the numbers: it is scored by Zero Slop's own
detector. Read it as how much of the surface register each method strips away, as
measured by the very thing that defines the register, and not as an independent
verdict.

| method | detector | followability | words |
|---|--:|--:|--:|
| original drafts | 69.0 | 0.46 | 159 |
| isatimur/de-slop | 23.4 | 0.41 | 137 |
| stacked pipeline | 21.2 | 0.38 | 114 |
| blader/humanizer | 19.3 | 0.46 | 135 |
| petergyang/no-ai-slop | 18.7 | 0.41 | 123 |
| hardikpandya/stop-slop | 15.7 | 0.33 | 116 |
| Zero Slop v1.0 (the judged build) | 10.4 | 0.36 | 128 |
| Zero Slop v1.2 | 9.8 | 0.07 | 159 |

Both Zero Slop rows are here because they are two different builds. v1.0 is
the one that won the 55 best-picks, and it did so while cutting drafts 22% shorter.
v1.2 holds the original length and no judge ever saw it, so treat that final
length column as a fact about v1.2 rather than a judged result.

A separate test asks a simpler question: can the meter tell obvious slop from
obvious human writing across LinkedIn, blog, social, Reddit and newsletter? It
separates the two by 77 points with an AUC of 1.000 and no overlap. The honest
caveat is that I wrote both classes myself, so it shows the meter agreeing with an
obvious judgment rather than proving it generalises to text in the wild. It lives
in `bench/discrimination/`, and the whole thing runs at about 1,100 documents a
second, fast enough to sit in CI without anyone noticing.

## limitations

The most useful thing the benchmark told me was where the skill fell down. It came
last of four on fidelity, 8.80 against 9.32, 9.58 and 9.66, and it was the only
tool in the entire run to earn a fabrication flag, for a rewrite that handed the
author a feeling they had never claimed. That one stings the most, because not
inventing things is the first rule the skill sets for itself. The cause was
structural: the gate measured vocabulary, rhythm, format and register, and nothing
in it measured whether the facts survived, so fidelity was riding on trust alone.
That is what `--fidelity` now repairs — it catches the mechanical half, a dropped
figure or an invented name or a feeling that was never there, though a claim
quietly reframed still slips past it, and I would rather say so than imply
otherwise.

A word on the number itself, because it misleads people. 9.5 is the floor, not a
grade. A document with nothing charged scores 9.5, and so does the bare string
`Hello`, so the span list is what you actually read and the composite is only the
summary sitting under it. For a sense of scale, the fifty raw AI drafts in
`bench/` average around 70, and the human writing in `data/corpus/` lands between
9 and 21.

The accuracy figures need the same honesty, because the ground under them is
thin: every one of them comes from corpora I wrote. Early on the scorer convicted
five of the eight human documents in its own repository, thanks to two arithmetic
bugs in the corroboration rule that were letting style carry a verdict with no
lexical evidence behind it. Both are fixed now, both are under regression test,
and the rate on ordinary human prose is down to zero of five — but five documents
is a direction, not a rate. A false-positive figure anyone should trust needs
something on the order of a thousand labelled human samples, and that corpus does
not exist here yet. It is the first item on the todo list, and not by accident.

Underneath all of that sits the regexes, which are brittle by their very nature.
Every false positive I have traced came from a pattern firing on legitimate
notation, and every miss from phrasing that nothing anticipated. Three of the four
channels already ignore specific wording, and the durable answer is more channels
of that kind rather than more patterns. It is also why this README scores around
30 and `references/rewrite-moves.md` scores in the 90s: they are documents about
slop, so they are built out of the exact words slop is made of, and no regex will
ever tell a specimen apart from an assertion.

## why this matters now

Four platforms shipped countermeasures within two weeks of each other, across late
July and early August 2026. LinkedIn added a reader-facing "seems like AI slop"
report, and flagged posts now lose reach beyond the author's own network. Snapchat
pulled wholly AI-generated video out of Spotlight. YouTube made generic and
template-based video ineligible for monetisation. Substack shipped a reader-facing
detector, citing research that up to 40% of social-media writing is now synthetic.

Every one of them drew the same line: AI that refines your work is fine, AI that
produces it is not. This tool sits on the right side of that line by construction,
because it never writes a draft, it only measures and rewrites yours. The
practical upshot is that reach now depends on whether readers believe a machine
wrote it, which quietly turns the AI accent from a question of taste into a
question of distribution.

## what it refuses

It will not invent a number, a name, an anecdote or a feeling. Hollow paragraphs
get flagged rather than padded out. Performed candor and forced hot takes are
turned away as the louder dialect of the same disease, and where disclosure is
required, it discloses. It also will not optimise against detector scores. A
detector like Pangram answers "did a machine produce this" for schools and
compliance teams, off a trained model with a published one-in-ten-thousand
false-positive rate; this answers a different question for the person doing the
writing, and the people who would want the first thing defeated are exactly the
ones it refuses to serve.

## todo

- **A labelled corpus at volume.** This is the blocker for every quantitative
  claim in the repo. RAID, HC3, M4 and AuTextification are all free, labelled, and
  cover email, social and blog. Tuning before it exists is precisely how the
  five-in-eight false-positive rate went unnoticed until someone measured it.
- **Stylometric channels that use no patterns at all.** The current research
  (NEULIF, [arXiv:2511.21744](https://arxiv.org/abs/2511.21744); cross-domain
  analysis, [arXiv:2606.04177](https://arxiv.org/abs/2606.04177)) puts function-word
  bigram frequency and sentence-length distribution at the top of the
  interpretable-feature list. They ignore specific wording, so a synonym swap
  cannot dodge them. On the twelve-sample corpus they show no signal at all, which
  is not a failure of the features but proof the corpus is far too small to
  calibrate them, and one more reason the labelled corpus has to come first.
- **Actually run the competitors.** The comparison is not a real head-to-head
  until each tool is executed and logged.
- **Fidelity that reads claims, not just entities.** It catches an invented name;
  it still misses a reframed argument.
- **Automatic capture for the reflect loop.** It has never promoted a pattern on
  its own, because it only learns from cuts the meter missed and the skill has
  usually stripped those already.

## repository

```
SKILL.md                    the runtime artifact: the loop the agent follows
scripts/slopscore.py        the scorer, stdlib only
scripts/learn.py            the reflect loop
scripts/calibrate.py        refit weights from a corpus; decay stale tells
data/patterns.json          74 weighted patterns, lexicon, riders
data/corpus/must-not-flag/  writing that must never be flagged
references/                 taxonomy, rewrite moves, platform modules, evidence
bench/                      the benchmark harness and the discrimination test
tests/test_all.py           58 tests
```

Run `python3 tests/test_all.py` and `python3 scripts/calibrate.py --selftest`. The
suite covers the detector, the learning gates, decay and throughput, plus a set of
guards that exist because each of these drifted at some point: documented counts
have to match the data, calibration anchors have to match the corpora, the plugin
mirror and the bundle have to be current, and no user prose is allowed to reach a
git-tracked file.

## acknowledgements

Builds on [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop) and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), all MIT;
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
and Kagi's [SlopStop](https://help.kagi.com/kagi/features/slopstop.html), which
arrived independently at the same two ideas this tool leans on, corroboration
before conviction and a first-class appeals path. The thirteen detection papers
behind the design are cited in [references/evidence.md](references/evidence.md);
the load-bearing ones are the post-training register finding (arXiv:2605.19516),
the excess-vocabulary method (Kobak et al., arXiv:2406.07016), and Liang et al.
(arXiv:2304.02819), which found that detectors misclassify over half of non-native
English writing and is the reason a non-native sample sits in the safety corpus.

MIT.
