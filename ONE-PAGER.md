# Zero Slop

A linter for the AI accent. It scores a draft 0-100, tells you which spans cost
what, rewrites it, and checks that the rewrite didn't invent anything.

The score is computed, not judged. That is the whole difference. You can put it in
CI, diff it across drafts, and argue with it, because every point is traceable
to something you can read.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then say "de-slop this" in any agent. No dependencies, no network, no account.

## the pitch, in one paragraph

Every other de-slop tool is a prompt. You paste your draft, it hands one back,
and you have no idea whether it got better or just different. Zero Slop measures
first, shows you the six spans carrying the score, rewrites, measures again, and
fails the rewrite if a figure went missing or a name appeared that wasn't in
your source. Then it learns from whatever you change before publishing.

## why now, specifically

Four platforms shipped countermeasures in two weeks, late July into August 2026.
LinkedIn added a reader-facing "seems like AI slop" report — flagged posts lose
reach beyond the author's own network. Snapchat dropped wholly AI-generated
video from Spotlight. YouTube made template-based video ineligible for
monetisation. Substack shipped a reader detector, citing research that up to 40%
of social-media writing is now synthetic.

They all drew the same line: AI that *refines* your work is fine, AI that
*produces* it is not. Zero Slop sits on the right side of it by construction.
It never writes a draft; it measures and rewrites yours.

The consequence is that reach is now downstream of whether readers think a
machine wrote it. This stopped being a matter of taste and became a
distribution problem.

## what it actually does

Four channels, every draft:

| channel | measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

Three quarters of the signal never looks at specific words, which is why a score
survives someone swapping synonyms to dodge a word list. The discrimination
corpus contains a post scoring 38.6 with zero charged spans, caught on
rhythm and shape alone, which is exactly what a lexicon-only tool misses.

Fusion is deliberately conservative: clusters convict, singles don't. Em-dashes
and formal register are habits, not evidence. Nineteenth-century oratory trips
both, so they only carry weight when lexical evidence corroborates.

## the numbers

Pooled over 100 blind verdicts on 50 drafts across six genres: **55 best-picks**
against blader/humanizer 40, no-ai-slop 5, de-slop 0. Wins the plurality against
a 25% chance rate (p = 1.7e-10). Statistically tied with blader head to head
(p = 0.15), which is worth saying because most tools in this category wouldn't.

Discrimination between obvious slop and obvious human writing across LinkedIn,
blog, social, Reddit and newsletter: AUC 1.000, 12/12, 77 points of separation.

False positives on ordinary human prose: 0 of 5, down from 5 of 8 after two
scoring bugs were found by measuring rather than reading.

Speed: ~1,100 docs/sec, 0.94 ms/doc. Fast enough to gate CI without anyone
noticing.

## the part I'd want to know before installing

It ranked **last of four on judge-rated fidelity** in the benchmark, and carried
the only fabrication flag. A rewrite invented a feeling the author never
described. The cause was structural: the gate measured vocabulary, rhythm,
format and followability, and nothing measured fidelity.

That's now a channel. `--fidelity` inventories figures, names, quotes and links
in the source and fails a rewrite that drops one or invents one. It still can't
see an invented *feeling*, so the judgment pass stays.

Also: 9.5 is the floor, not a grade. `Hello` scores 9.5. The accuracy numbers
above rest on corpora I authored, which shows the meter agrees with an obvious
judgment, not that it generalises. A real false-positive rate needs a thousand
labelled samples and that corpus doesn't exist yet.

## it learns from your edits

The most honest signal a linter can get is what you change *after* it hands the
draft back. Strike a phrase before publishing and that phrase was a tell it
missed.

One edit changes nothing. A span becomes a pattern only after three independent
documents cut it, because a single diff can't tell a stylistic tell from an
author trimming for length. The loop runs both ways. A pattern you overrule
three times loses half its weight, because a meter that can only grow ends up
flagging everything.

Reflection data stays in `~/.zero-slop/`, never the repo. Sharing upstream is
opt-in and prints the whole payload first.

## what it refuses

No invented numbers, names, anecdotes or feelings. Hollow paragraphs get
flagged, not padded. Performed candor and forced hot takes are rejected as the
louder dialect of the same disease. Where disclosure is required, disclose.

It also doesn't optimise against detector scores. Tools like Pangram answer "did
a machine produce this" for schools and compliance teams. This answers a
different question for a different person, and the people who'd want the first
thing defeated are the ones it refuses to serve.

## who it's for

People who publish under their own name and would rather not be pattern-matched
to a chatbot. Comms teams who need a number they can put in a review. Engineering
teams who want slop to fail CI like any other lint rule. Researchers who need the
formal register left intact: the research module forbids moves the general
ladder prescribes, because contractions and short punchy sentences are
themselves a tell in a journal abstract.

---

MIT · [github.com/manavmishra/ZeroSlop](https://github.com/manavmishra/ZeroSlop)
· 56 tests · builds on no-ai-slop, humanizer, de-slop, stop-slop, Wikipedia's
Signs of AI writing, Kagi's SlopStop, and thirteen detection papers cited in the
repo.
