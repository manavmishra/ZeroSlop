# Zero Slop

Zero Slop is a linter for the AI accent. It scores a draft from 0 to 100, shows
which words cost what, rewrites it, and proves the rewrite kept every fact and
invented nothing. The score is computed rather than judged, so it goes in CI, and
every point traces back to a span you can read.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then say "de-slop this" in any agent. No dependencies, no network, no account.

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

## What It Is

A linter and rewriter for people who publish under their own name. It tells you
whether a reader will think a machine wrote your draft, and it removes the parts
that give that impression, without touching your facts.

It is a de-slopper, not a writer. It subtracts the tells and returns your words,
your structure, and your voice intact. A draft that already reads human comes back
unchanged.

## What It Is Not

It is not a detector. It does not classify authorship, sell to schools or
compliance teams, or optimise against detector scores. Those answer a different
question for a different reader, and the people who would want the first thing
defeated are the ones this tool refuses to serve.

## Why It Exists Now

Four platforms shipped countermeasures within two weeks of each other in late July
and August 2026. LinkedIn added a reader-facing "seems like AI slop" report, and
flagged posts lose reach beyond the author's own network. Snapchat pulled wholly
AI-generated video from Spotlight. YouTube made template-based video ineligible for
monetisation. Substack shipped a reader detector, citing research that up to 40% of
social-media writing is now synthetic.

Each drew the same line: AI that refines your work is fine, AI that produces it is
not. Zero Slop sits on the refining side by construction, because it never writes a
draft, it measures and rewrites yours. Reach now depends on whether readers believe
a machine wrote it, which turns the AI accent from a question of taste into a
question of distribution.

## How It Works

Four channels run on every draft, and three never look at specific words, so a
synonym swap does not move the score.

| channel | measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

The four fuse cautiously, because a single stylistic habit is not evidence. An
em-dash or a formal register describes a great deal of excellent human writing, so
those carry weight only once the lexical channel agrees. Clusters convict, singles
do not.

The rewrite runs in two passes, stripping the tells first and rebuilding toward an
expert register second, and it checks its own work. `--fidelity` inventories the
figures, names, quotes and stated feelings in the source and fails the rewrite if
any went missing, or if any appeared that was not there before.

## The Numbers

Fifty AI-typical drafts, six genres, judged blind on shuffled labels. Pooled over
100 verdicts, Zero Slop takes 55 best-picks against blader/humanizer's 40,
no-ai-slop's 5 and de-slop's 0. It wins the plurality against a 25% chance rate
(p = 1.7e-10) and is statistically tied with blader head to head (p = 0.15), which
is worth stating because most tools in this category leave it out.

A separate test tells obvious slop from obvious human writing across five genres,
separating the two by 77 points, AUC 1.000. On ordinary human prose the
false-positive rate is now zero of five, down from five of eight after two scoring
bugs were fixed. Throughput is about 1,100 documents a second.

Every number rests on corpora authored for the repo, stated plainly wherever they
appear. They show the meter agreeing with an obvious judgment, not that it
generalises, and a trustworthy false-positive figure needs a labelled corpus at
volume that does not exist yet. That corpus leads the roadmap, ahead of the
research-backed stylometric channels (function-word bigrams and sentence-length
distribution, per NEULIF arXiv:2511.21744) that wait on it for calibration.

## The Honest Weakness

In the benchmark, Zero Slop came last of four on judge-rated fidelity, and it was
the only tool to carry a fabrication flag, for a rewrite that gave the author a
feeling they never described. Nothing in the loop measured fidelity at the time, so
the property the tool cares about most was riding on instruction alone. `--fidelity`
exists because of that and now catches the mechanical half, an invented figure or
name or feeling, while a claim quietly reframed still needs the judgment pass.
Publishing the result that went against it is the reason to trust the ones that did
not.

## It Learns From Your Edits

The most honest signal a linter can get is what you change after it hands the draft
back. A span becomes a new pattern only after three separate documents cut it, and a
pattern you overrule three times loses half its weight, so the meter sharpens in
both directions with use. A profile built from a sample of your own writing quiets
the words you use by habit, without touching anyone else's meter. All of it stays on
your machine, and sharing what it learned upstream is opt-in, carrying spans and
counts but never your source text.

---

MIT · [github.com/manavmishra/ZeroSlop](https://github.com/manavmishra/ZeroSlop)
· v1.6.0 · 62 tests · builds on no-ai-slop, humanizer, de-slop and stop-slop,
Wikipedia's Signs of AI writing, Kagi's SlopStop, and the detection literature
cited in the repository.
