# Zero Slop

A linter for the AI accent. It scores a draft from 0 to 100, shows you which
spans cost what, rewrites it, and checks that the rewrite kept your facts and
invented nothing. The score is computed rather than judged, so you can gate CI
on it, diff it across revisions, and argue with any number it gives you, because
every point traces to something you can read.

It is not a detector. It will not tell you whether a machine wrote something. It
tells you whether a reader will *think* one did, which is a different question,
and the only one a writer can do anything about.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then say "de-slop this" in any agent. No dependencies, no network, no account:
one standard-library Python file does the scoring, and nothing leaves your
machine. It is still actively wrong about some things, all of them listed under
[limitations](#limitations) and [todo](#todo).

## how it reads a draft

Here is a sentence a product marketer would call finished:

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

Six spans carry the whole score and each one names itself. `seamless` is charged
twice on purpose, once as marketing register and once as vocabulary, because two
independent channels agreeing is stronger evidence than either alone. `leveraged`
scores only 2, because it is a *rider*: silent in "we leveraged the existing
index", charged here because marketing words share its sentence. That is the
core idea the whole scorer is built on, and the next section is how it works.

Strike the six spans and one fact is left standing:

> We cut onboarding setup time by 40% using AI.

```console
$ python3 scripts/slopscore.py --explain rewrite.md
AI-likelihood: 9.5/100  [clean]
  tell density : 0.00 weighted hits /100w (8 words)

  charged spans: none — the score is rhythm and format only
```

Twenty-two words down to eight, and the survivor is the 40%. That ratio is the
point. Most of the original was decoration around one measurement, which is what
the AI accent usually turns out to be once you look at it span by span.

## how it works

Four channels run on every draft. Three of them never look at specific words,
which is why a score survives someone swapping synonyms to dodge a word list.

| channel | measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence-length variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

They fuse into one number, and the fusion is deliberately cautious, because a
single stylistic habit is not evidence. Em-dash density and a formal register
describe plenty of excellent human prose, so they only carry weight when the
lexical channel corroborates them. The rule is that clusters convict and singles
do not, and getting the arithmetic of it wrong is the single largest way a
detector like this fails. It happened here, and how it was caught is under
[limitations](#limitations).

A rider is the mechanism that makes the pattern meter precise instead of
trigger-happy. Words like *leverage*, *robust*, *elevated* and *landscape* are
ordinary technical vocabulary until a marketing trigger shares their sentence, so
they sit in a separate list and score nothing on their own. "Elevated write
volume" in a runbook is silent; "elevate your brand with our seamless platform"
is not.

Once a draft is scored, the rewrite runs as two passes rather than one. The first
strips the tells, touching nothing else. The second rebuilds toward an expert
register on the cleaned text, with the tells already gone so they cannot mask a
substance judgment. Benchmarking is what settled on that order: a strip-then-build
sequence beat a single do-everything rewrite because each pass keeps one focus.

## it verifies its own rewrite

The rewrite is not allowed to invent things. This used to be a rule the agent was
asked to honour, and asking was not enough — in the benchmark below it was the
one dimension the skill lost on. So it is now checked:

```bash
python3 scripts/slopscore.py --fidelity original.md rewrite.md
```

The check inventories the figures, names, quotes, links and stated feelings in
your source, and exits non-zero if any went missing, or if any appeared that was
not there before. The second half is the one that matters. A dropped number is
visible to you; an invented one is not, and invention is precisely what the
benchmark caught the skill doing. It cannot see a reframed claim or a shifted
emphasis, so the judgment pass still applies to those, and every run says so.

## it learns from your edits

The most honest signal a linter can get is what you change *after* it hands the
draft back. If you strike a phrase before publishing, that phrase was a tell it
missed, in your genre and your voice, from the model generation you actually
face.

```bash
python3 scripts/learn.py --reflect --produced out.md --shipped final.md
python3 scripts/learn.py --promote --apply
```

One edit changes nothing. A span becomes a pattern only after three independent
documents cut it, because a single diff cannot tell a stylistic tell from an
author trimming for length. An early version watched one writer delete "the
people is the standard we hold ourselves to" and proposed it as a tell; it was
just content. The loop also runs in reverse: a pattern you overrule three times
loses half its weight, because a meter that can only grow ends up flagging
everything.

Reflection data lives in `~/.zero-slop/`, never in the repository, and derives
from your own drafts. Sharing what it learned upstream is one opt-in command that
prints the entire payload, carrying spans and counts but no source text, before
it writes anything.

## benchmarks

Fifty AI-typical drafts across six genres, judged blind on shuffled labels. Read
this as a design study rather than a head-to-head: the competitor outputs in
`bench/outputs/` were written to represent each tool's published prompt rather
than produced by running it, only Zero Slop's rewrites iterated against a gate,
and the judge prompts and model ids were not recorded.

Run one gave Zero Slop 32 of 50 best-picks; a replication with fresh judges on
identical rewrites gave 23. Cohen's kappa is 0.12, so judges barely agree on
"best" and any single run is noise. Pooled across 100 verdicts:

| method | best-picks | composite r1 | composite r2 |
|---|--:|--:|--:|
| Zero Slop | 55 | 8.01 | 7.51 |
| blader/humanizer | 40 | 7.82 | 7.51 |
| petergyang/no-ai-slop | 5 | 6.96 | 6.87 |
| isatimur/de-slop | 0 | 6.35 | 6.60 |

It wins the plurality against a 25% chance rate (p = 1.7e-10, 95% CI [45%, 64%]),
is not statistically separable from blader/humanizer head to head (p = 0.15), and
both beat the other two decisively (p < 1e-7).

The deterministic panel below is scored by Zero Slop's own detector, so read it
as how much surface register each method removes as measured by the thing that
defines the register, not as an independent verdict:

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

Both Zero Slop rows appear because they are different builds. v1.0 won the 55
best-picks and cut drafts 22% shorter; v1.2 holds the original length and no
judge ever saw it, so the length column is a property of v1.2, not a judged
result.

A separate test asks whether the meter can tell obvious slop from obvious human
writing across LinkedIn, blog, social, Reddit and newsletter. It separates them
by 77 points with an AUC of 1.000 and no overlap, with the honest caveat that I
wrote both classes, so it shows the meter agreeing with an obvious judgment
rather than generalising to text in the wild. It runs in `bench/discrimination/`.
Throughput is about 1,100 documents a second, fast enough to gate CI unnoticed.

## limitations

The benchmark's most useful result was the one that went against the skill. It
ranked last of four on judge-rated fidelity, 8.80 against 9.32, 9.58 and 9.66,
and carried the only fabrication flag in the whole run, because a rewrite
invented a feeling the author never described. Nothing in the loop measured
fidelity, so the property the tool claims to protect was enforced by instruction
alone. The `--fidelity` channel above exists because of that, and now catches the
mechanical half of it — invented figures, names and stated feelings. A reframed
claim it still cannot see.

The score has a floor of 9.5, not a grade. Any document with zero charged spans
scores 9.5, and so does the string `Hello`, so the span list is the reading and
the composite is the summary. For scale, the 50 raw AI drafts in `bench/` average
70 and the human writing in `data/corpus/` lands between 9 and 21.

The accuracy numbers rest on corpora I wrote. Scoring the human-written documents
in this repo once convicted five of eight, from two arithmetic bugs in the
corroboration rule that let style convict without lexical evidence; both are fixed
and under regression test, and the rate on ordinary human prose is now zero of
five. But five documents is a direction, not a rate. A defensible false-positive
figure needs on the order of a thousand labelled human samples, and that corpus
does not exist here yet, which is why it leads the todo list.

Regexes are brittle by construction. Every false positive traces to one firing on
legitimate notation, and every miss to phrasing nothing anticipated. Three of the
four channels are already blind to specific wording, and the durable answer is
more channels of that kind rather than more patterns.

Finally, documentation about writing scores as slop, correctly. This README
scores around 30, and every charged span is a word it is explaining;
`references/rewrite-moves.md` scores in the 90s because it is a catalogue of slop
examples. No regex distinguishes a specimen from an assertion.

## why this matters now

Four platforms shipped countermeasures within two weeks of each other, late July
into August 2026. LinkedIn added a reader-facing "seems like AI slop" report, and
flagged posts lose reach beyond the author's own network. Snapchat dropped wholly
AI-generated video from Spotlight. YouTube made generic and template-based video
ineligible for monetisation. Substack shipped a reader detector, citing research
that up to 40% of social-media writing is now synthetic.

Every one of them drew the same line: AI that refines your work is fine, AI that
produces it is not. This sits on the right side of that line by construction,
because it never writes a draft, it measures and rewrites yours. The practical
consequence is that reach is now downstream of whether readers think a machine
wrote it, which turns the AI accent from a matter of taste into a distribution
problem.

## what it refuses

No invented numbers, names, anecdotes or feelings; hollow paragraphs get flagged
rather than padded; performed candor and forced hot takes are rejected as the
louder dialect of the same disease; and where disclosure is required, it
discloses. It also does not optimise against detector scores. A detector like
Pangram answers "did a machine produce this" for schools and compliance teams,
from a trained model with a published one-in-ten-thousand false-positive rate.
This answers a different question for the person doing the writing, and the people
who would want the first thing defeated are the ones it refuses to serve.

## todo

- **A labelled corpus at volume.** The blocker for every quantitative claim.
  RAID, HC3, M4 and AuTextification are free, labelled, and cover email, social
  and blog. Tuning before this exists is exactly how the five-in-eight
  false-positive rate survived unnoticed until it was measured.
- **Stylometric channels that use no patterns at all.** Current research
  (NEULIF, [arXiv:2511.21744](https://arxiv.org/abs/2511.21744); cross-domain
  analysis, [arXiv:2606.04177](https://arxiv.org/abs/2606.04177)) puts
  function-word bigram frequency and sentence-length distribution at the top of
  the interpretable-feature list. They are blind to specific wording, so they
  cannot be dodged by swapping synonyms. Measured on the twelve-sample corpus
  they show no signal — which is not a failure of the features but proof the
  corpus is too small to calibrate them, and the reason the labelled corpus
  above has to come first.
- **Actually run the competitors.** The comparison is not a real head-to-head
  until each tool is executed and logged.
- **Fidelity that sees claims, not just entities.** It catches an invented name;
  it misses a reframed argument.
- **Automatic capture for the reflect loop**, which has never promoted a pattern
  on its own because it only learns from cuts the meter missed, and the skill has
  already stripped what it knows.

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

Run `python3 tests/test_all.py` and `python3 scripts/calibrate.py --selftest`.
The suite covers the detector, the learning gates, decay, throughput, and a set
of guards that exist because these things drifted before: documented counts must
match the data, calibration anchors must match the corpora, the plugin mirror and
bundle must be current, and no user prose may enter a git-tracked file.

## acknowledgements

Builds on [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop) and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), all MIT;
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
Kagi's [SlopStop](https://help.kagi.com/kagi/features/slopstop.html), which
converged independently on corroboration-before-conviction and a first-class
appeals path; and thirteen detection papers cited in
[references/evidence.md](references/evidence.md), the load-bearing ones being the
post-training register finding (arXiv:2605.19516), the excess-vocabulary method
(Kobak et al., arXiv:2406.07016), and Liang et al. (arXiv:2304.02819), which found
detectors misclassify over half of non-native English writing and is the reason a
non-native sample sits in the safety corpus.

MIT.
