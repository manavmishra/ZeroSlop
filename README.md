# Zero Slop

A linter for the AI accent. It scores a draft 0-100, tells you which spans cost
what, and rewrites it. The score is computed, not judged, so you can put it in
CI and argue with it.

It is not a detector. It won't tell you whether a machine wrote something. It
tells you whether a reader will *think* one did, which is a different question
and the only one a writer can act on.

Still actively wrong about things. See [todos](#todos).

## install

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then say "de-slop this" in any agent. Or clone it and use the scorer on its own:

```bash
git clone https://github.com/manavmishra/ZeroSlop.git
cd ZeroSlop
printf "We're thrilled to announce a seamless cutting-edge solution.\n" | python3 scripts/slopscore.py --explain
```

No dependencies. One stdlib Python file does the scoring. Nothing phones home.

## quick start

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

Six spans carry the whole thing and each one names itself. `seamless` gets
charged twice on purpose, once as marketing register and once as vocabulary,
because those are two independent channels agreeing, which is worth more than
either alone. `leveraged` only scores 2, because it's a *rider*: silent in "we
leveraged the existing index", charged here because marketing words share its
sentence.

Strike the six and one fact is left standing:

> We cut onboarding setup time by 40% using AI.

```console
$ python3 scripts/slopscore.py --explain rewrite.md
AI-likelihood: 9.5/100  [clean]
  tell density : 0.00 weighted hits /100w (8 words)

  charged spans: none — the score is rhythm and format only
```

22 words to 8, and the survivor is the 40%. That ratio is the whole point. Most
of the original was decoration around one measurement, which is what the AI
accent usually turns out to be once you look.

Run both yourself:

```bash
printf "We're thrilled to announce that our team has leveraged cutting-edge AI to deliver a seamless onboarding experience, reducing setup time by 40%%.\n" | python3 scripts/slopscore.py --explain
printf "We cut onboarding setup time by 40%% using AI.\n" | python3 scripts/slopscore.py --explain
```

## about that 9.5

It's the floor, not a grade. Any document with zero charged spans scores 9.5.
So does the string `Hello`. Read the span list first and the number second.

For scale: the 50 raw AI drafts in [`bench/`](bench/) average 70, and the
certified-human writing in [`data/corpus/`](data/corpus/must-not-flag/) lands
between 9 and 21. That makes the number useful for ranking drafts
against each other and for a CI threshold. It is not a verdict on one text
alone, and it says nothing about whether the sentence was worth writing, which
is why every run prints what it did not measure.

## how it works

Four channels, all interpretable, all computed on every draft.

| channel | what it measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence-length variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

Only the first reads specific words. That's why a score survives someone
swapping synonyms to dodge a word list — three quarters of the signal never
looked at the words.

They fuse into one number, but the fusion is deliberately conservative:
clusters convict, singles don't. Em-dash density and formal register are
stylistic habits, not evidence on their own. Nineteenth-century oratory trips
both, so they only carry weight when lexical evidence corroborates them. Getting that
arithmetic wrong once made the scorer convict 5 of 8 human-written documents in
this very repo. See [accuracy](#accuracy).

```bash
python3 scripts/slopscore.py --dna before.md after.md   # which channel carried the slop
python3 scripts/slopscore.py --gate 25 draft.md         # exit 1 on failure, for CI
python3 scripts/slopscore.py --batch docs/              # whole directory, worst first
python3 scripts/slopscore.py --formal abstract.txt      # research register
```

### fidelity

The rewrite must not invent things. This used to be a rule the agent was asked
to honour; now it's checked:

```bash
python3 scripts/slopscore.py --fidelity original.md rewrite.md
```

It inventories figures, names, quotes and links in the source and exits
non-zero if any went missing, or if any appeared that wasn't there before. The
second half is the one that matters. A dropped number is visible to the author;
an invented one isn't.

It only sees figures, names, quotes and links. It cannot see an invented
*feeling*, which is exactly the failure that made me build it (below).

### it learns from your edits

The most honest signal a linter can get is what you change *after* it hands the
draft back. If you strike a phrase before publishing, that phrase was a tell it
missed.

```bash
python3 scripts/learn.py --reflect --produced out.md --shipped final.md
python3 scripts/learn.py --promote --apply
```

One edit changes nothing. A span becomes a pattern only after three independent
documents cut it, because a single diff can't tell a stylistic tell from an
author trimming for length. An early version watched someone delete "the people
is the standard we hold ourselves to" and proposed it as a tell. It was
just content.

The loop runs both directions: a pattern you overrule three times loses half
its weight. A meter that can only grow ends up flagging everything.

Reflection data lives in `~/.zero-slop/`, never in the repo. `--export` shares what
it learned upstream with no source text attached, and prints the whole payload
before writing anything.

## benchmarks

Fifty AI-typical drafts, six genres, blind judges on shuffled labels.

**This is a design study, not a head-to-head.** The competitor outputs in
`bench/outputs/` were written to represent each tool's published prompt rather
than produced by running it, and only Zero Slop's rewrites iterated against a
gate. Judge prompts and model ids weren't recorded. Weigh accordingly.

Run one gave Zero Slop 32 of 50 best-picks. A replication with fresh judges on
identical rewrites gave 23. Cohen's kappa 0.12, so judges barely agree on "best" and one run in this
category is noise. Pooled over 100 verdicts:

| method | best-picks | composite r1 | composite r2 |
|---|--:|--:|--:|
| **Zero Slop** | **55** | **8.01** | 7.51 |
| blader/humanizer | 40 | 7.82 | 7.51 |
| petergyang/no-ai-slop | 5 | 6.96 | 6.87 |
| isatimur/de-slop | 0 | 6.35 | 6.60 |

Wins the plurality against a 25% chance rate (p = 1.7e-10, 95% CI [45%, 64%]).
**Not statistically separable from blader/humanizer** head to head (p = 0.15).
Both beat the other two decisively (p < 1e-7).

Deterministic panel, scored by Zero Slop's own detector — so read it as "how
much surface register each method removes, as measured by the thing that
defines the register", not as an independent verdict:

| method | detector | followability | words |
|---|--:|--:|--:|
| original drafts | 69.0 | 0.46 | 159 |
| isatimur/de-slop | 23.4 | 0.41 | 137 |
| stacked pipeline | 21.2 | 0.38 | 114 |
| blader/humanizer | 19.3 | 0.46 | 135 |
| petergyang/no-ai-slop | 18.7 | 0.41 | 123 |
| hardikpandya/stop-slop | 15.7 | 0.33 | 116 |
| Zero Slop v1.0 *(the judged build)* | 10.4 | 0.36 | 128 |
| **Zero Slop v1.2** | **9.8** | **0.07** | **159** |

Both Zero Slop rows are shown because they're different builds. v1.0 won the 55
best-picks and cut drafts 22% shorter. v1.2 holds length and no judge ever saw
it. Don't read the length column as a judged result.

There's also a discrimination test — can it tell obvious slop from obvious human
writing across LinkedIn, blog, social, Reddit and newsletter? AUC 1.000, 12/12,
77 points of separation, no overlap. With the caveat that I wrote both classes,
so it shows the meter agrees with an obvious judgment, not that it generalises.

```bash
python3 bench/discrimination/evaluate.py
```

Speed: ~1,100 docs/sec, 0.94 ms/doc, a 15,000-word document in 0.16s.

## the result that went against me

Zero Slop ranked **last of four on judge-rated fidelity**, 8.80 against blader
9.32, petergyang 9.58 and de-slop 9.66, and carried the only fabrication flag in
the whole benchmark. A rewrite invented a feeling the author never described,
and two independent judges caught it.

That is the exact thing the skill's first rule forbids, and it's the most useful
thing the benchmark produced. The cause was structural: the gate measured
vocabulary, rhythm, format and followability, and nothing measured fidelity.
The property I claimed mattered most was enforced by instruction alone.

`--fidelity` exists because of that. It catches the mechanical half: invented
figures and names. It still cannot catch an invented feeling, so the judgment
pass stays.

## accuracy

Scoring the human-written docs in this repo, with quoted specimens stripped,
once convicted **5 of 8**. Two bugs: the corroboration floor was 0.45, handing
style 45% of its weight to text with no lexical evidence at all, and the clamp
meant to catch the rest keyed on hit *count*, so one weight-2.5 tell in 392
words scored `AGENTS.md` at 59.2. Both fixed, both under regression test. Now
**0 of 5**.

That's a direction, not a rate. You can't establish a 1% false-positive rate
from five documents. It needs on the order of a thousand labelled human
samples, and that corpus doesn't exist here yet.

Three docs here still score 59-96, correctly. `references/rewrite-moves.md` and
`overcorrection.md` are catalogues of slop examples; `evidence.md` discusses
"delve" and "meticulous" as vocabulary. No regex distinguishes a specimen from
an assertion. If you lint documentation *about* writing, expect this.

This README scores about 30, and every charged span is a word it's explaining.

## why this matters now

Four platforms shipped countermeasures within two weeks of each other in late
July and early August 2026. LinkedIn added a reader-facing "seems like AI slop"
report; flagged posts lose reach beyond the author's own network. Snapchat
dropped wholly AI-generated video from Spotlight. YouTube made generic and
template-based video ineligible for monetisation. Substack shipped a reader
detector, citing research that up to 40% of social-media writing is now
synthetic.

They all drew the same line: AI that *refines* your work is fine, AI that
*produces* it is not. This sits on the right side of it — it never writes a
draft, it measures and rewrites yours.

The practical consequence is that reach is now downstream of whether readers
think a machine wrote it. That makes this a distribution problem, not a matter
of taste.

## what it refuses

No invented numbers, names, anecdotes or feelings. Hollow paragraphs get
flagged, not padded. Performed candor and forced hot takes are rejected as the
louder dialect of the same disease. Where disclosure is required, disclose.

It also doesn't optimise against detector scores. Tools like Pangram answer
"did a machine produce this" for schools and compliance teams, from a trained
model with a published 1-in-10,000 false-positive rate. This answers a
different question for a different person, and the people who'd want the first
thing defeated are the ones it refuses to serve.

## todos

- **A labelled corpus at volume.** This is the blocker for everything
  quantitative. RAID, HC3, M4 and AuTextification are free, labelled, and cover
  email/social/blog. Every accuracy number above rests on samples I authored,
  and tuning before this corpus exists is precisely how the 5-in-8 false
  positive rate survived unnoticed.
- **Channels that use no patterns at all.** Regexes are brittle by
  construction. Every false positive traced to one firing on legitimate
  notation, every miss to phrasing nothing anticipated. Function-word
  distribution (the Mosteller-Wallace signal), hapax rate, and sentence-opener
  diversity are all stdlib-computable and blind to wording.
- **Actually run the competitors.** The benchmark comparison isn't a real
  head-to-head until each tool is executed and logged.
- **A fidelity channel that sees claims, not just entities.** It catches an
  invented name; it misses an invented feeling, which is the failure that
  motivated it.
- **The reflect loop has never promoted a pattern automatically.** By
  construction: it only learns from cuts the meter missed, and the skill has
  already stripped what it knows. The capture step also needs to stop requiring
  a CLI invocation nobody will run.

## repo layout

```
SKILL.md                  the runtime artifact — the loop the agent follows
scripts/slopscore.py      the scorer, stdlib only
scripts/learn.py          the reflect loop
scripts/calibrate.py      refit weights from your own corpus; decay stale tells
data/patterns.json        74 weighted patterns + lexicon + riders
data/corpus/must-not-flag/  writing that must never be flagged
references/               the taxonomy, rewrite moves, platform modules, evidence
bench/                    the benchmark harness and the discrimination test
tests/test_all.py         56 tests
```

## tests

```bash
python3 tests/test_all.py
python3 scripts/calibrate.py --selftest
```

The suite covers the detector, the learning gates, decay, CLI contracts,
throughput, diagram geometry, and a set of guards that exist because these
things drifted before: documented counts must match the data files, calibration
anchors must match the corpora, the bundle and plugin mirror must be current,
and no user prose may enter a git-tracked file.

## acknowledgements

Builds on [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop) and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), all MIT.
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).
Kagi's [SlopStop](https://help.kagi.com/kagi/features/slopstop.html), which
converged independently on corroboration-before-conviction and an appeals path.
Thirteen detection papers, cited in
[references/evidence.md](references/evidence.md) — the load-bearing ones are
the post-training register finding (arXiv:2605.19516), the excess-vocabulary
method (Kobak et al., arXiv:2406.07016), and Liang et al.
(arXiv:2304.02819), which found detectors misclassify over half of non-native
English writing and is why there's an ESL sample in the safety corpus.

MIT.
