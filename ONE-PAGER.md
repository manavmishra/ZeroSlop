# Zero Slop

**Add taste to your output, or fix your slop.** Zero Slop is a linter for the AI
accent. It scores a draft from 0 to 100, shows you which words cost what, rewrites
it, and checks the rewrite kept every fact and made nothing up. The score is computed rather than judged, which is the whole point:
you can gate CI on it, diff it across revisions, and argue with any number,
because each one traces back to a span you can read.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then say "de-slop this" in any agent. No dependencies, no network, no account.

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

## what it is, and what it is not

It is a linter and rewriter for people who publish under their own name. It tells
you whether a reader will think a machine wrote your draft, and it fixes the parts
that give them that impression, without ever touching your facts.

What it is not is a detector. It will not classify someone else's work as
AI-generated, it does not sell to schools or compliance teams, and it will not
optimise against detector scores. That is a different product answering a
different question, and the people who would want it defeated are exactly the ones
this tool refuses to serve.

## why it exists now

Four platforms shipped countermeasures inside two weeks of each other in late July
and August 2026. LinkedIn added a reader-facing "seems like AI slop" report, and
flagged posts now lose reach beyond the author's own network. Snapchat pulled
wholly AI-generated video from Spotlight. YouTube made template-based video
ineligible for monetisation. Substack shipped a reader detector, citing research
that up to 40% of social-media writing is now synthetic.

Each of them drew the same line: AI that refines your work is fine, AI that
produces it is not. Zero Slop sits on the right side of that line by construction,
because it never writes a draft, it only measures and rewrites yours. The upshot
is that reach now depends on whether readers believe a machine wrote it, which
quietly turns the AI accent from a matter of taste into a matter of distribution.

## how it works

Four channels run on every draft, and three of them never look at specific words
at all, which is why a score holds up even when someone swaps synonyms to slip
past a word list.

| channel | measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

The fusion is cautious by design, because a single stylistic habit is not evidence
of anything. An em-dash or a formal register describes a great deal of excellent
human writing, so those only carry weight once the lexical channel backs them up.
Clusters convict, singles do not. That rule matters enough that getting its
arithmetic wrong, once, made the scorer convict five of the eight human documents
in its own repository, a mistake the repo documents rather than hides.

Then it rewrites in two passes, stripping the tells first and rebuilding toward an
expert register second, and it checks its own work. `--fidelity` inventories the
figures, names, quotes and stated feelings in your source and fails the rewrite if
any of them went missing, or if any showed up that was not there before.

## the numbers

Fifty AI-typical drafts, six genres, judged blind on shuffled labels. Pooled over
100 verdicts, Zero Slop takes 55 best-picks against blader/humanizer's 40,
no-ai-slop's 5 and de-slop's 0. It wins the plurality against a 25% chance rate
(p = 1.7e-10), and it is statistically tied with blader head to head (p = 0.15),
which is worth saying out loud because most tools in this category would quietly
leave it out.

A separate test asks whether the meter can tell obvious slop from obvious human
writing across five genres, and it separates the two by 77 points with an AUC of
1.000. On ordinary human prose the false-positive rate is now zero of five, down
from five of eight once two scoring bugs were found and fixed. The whole thing
runs at roughly 1,100 documents a second.

Every one of those numbers rests on corpora the author wrote, and that is stated
plainly wherever they appear. They show the meter agreeing with an obvious
judgment, not that it generalises to text in the wild, and a false-positive figure
anyone should trust needs a labelled corpus at volume that does not exist here yet.
That corpus is the first item on the roadmap, ahead of the research-backed
stylometric channels (function-word bigrams and sentence-length distribution, per
NEULIF arXiv:2511.21744) that depend on it for calibration.

## the honest weakness

In the benchmark, Zero Slop came last of four on judge-rated fidelity, and it was
the only tool to carry a fabrication flag, for a rewrite that handed the author a
feeling they had never claimed. Nothing in the loop measured fidelity at the time,
so the property the tool cares about most was riding on instruction alone. That is
the whole reason `--fidelity` exists, and it now catches the mechanical half of
the problem, an invented figure or name or feeling, while a claim quietly reframed
still needs the judgment pass. Publishing the result that went against it is the
reason to trust the ones that did not.

## it learns from your edits, and adapts to you

The most honest signal a linter can get is what you change after it hands the draft
back. A span becomes a new pattern only once three separate documents have cut it,
and a pattern you overrule three times loses half its weight, so the meter sharpens
in both directions the more it is used. It will also learn you in particular: build
a profile from a sample of your own writing, and it stops charging you for the
tell-words you reach for by reflex, while everyone else's meter stays untouched and
real slop still gets caught. All of this stays on your machine, and sharing what it
learned upstream is opt-in, carrying spans and counts but never your source text.

---

MIT · [github.com/manavmishra/ZeroSlop](https://github.com/manavmishra/ZeroSlop)
· v1.6.0 · 62 tests · builds on no-ai-slop, humanizer, de-slop and stop-slop,
Wikipedia's Signs of AI writing, Kagi's SlopStop, and the detection literature
cited in the repository.
