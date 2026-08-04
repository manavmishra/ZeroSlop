# Zero Slop

A linter for the AI accent. It scores a draft from 0 to 100, shows which spans
cost what, rewrites it, and checks the rewrite kept every fact and invented
nothing. The score is computed rather than judged, which is the whole point:
you can gate CI on it, diff it across revisions, and argue with any number,
because every point traces to a span you can read.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then say "de-slop this" in any agent. No dependencies, no network, no account.

## what it is, and is not

It is a linter and rewriter for people publishing under their own name. It tells
you whether a reader will think a machine wrote your draft, and fixes the parts
that make them think so, without touching your facts.

It is not a detector. It will not classify someone else's work as AI-generated,
it does not sell to schools or compliance teams, and it deliberately does not
optimise against detector scores. That is a different product answering a
different question, and the people who would want it defeated are the ones this
tool refuses to serve.

## why it exists now

Four platforms shipped countermeasures within two weeks of each other in late
July and August 2026. LinkedIn added a reader-facing "seems like AI slop"
report, and flagged posts lose reach beyond the author's own network. Snapchat
dropped wholly AI-generated video from Spotlight. YouTube made template-based
video ineligible for monetisation. Substack shipped a reader detector, citing
research that up to 40% of social-media writing is now synthetic.

They all drew the same line: AI that refines your work is fine, AI that produces
it is not. Zero Slop sits on the right side of it by construction, because it
never writes a draft, it measures and rewrites yours. The consequence is that
reach is now downstream of whether readers think a machine wrote it, which turns
the AI accent from a matter of taste into a distribution problem.

## how it works

Four interpretable channels run on every draft, and three of them never look at
specific words, which is why a score survives someone swapping synonyms to dodge
a word list.

| channel | measures | reads wording? |
|---|---|---|
| pattern meter | 74 weighted patterns, 55-term lexicon, 13 context-gated riders | yes |
| rhythm | sentence variance, uniformity, paragraph shape | no |
| followability | comma chains, long-word pileups, 38+ word sentences | no |
| format | em-dash density, emoji, hashtags, bold spam | no |

The fusion is deliberately cautious. A single stylistic habit is not evidence,
because an em-dash or a formal register describes plenty of excellent human
prose, so those only carry weight when the lexical channel corroborates them.
Clusters convict, singles do not. That principle is also load-bearing enough
that getting its arithmetic wrong once made the scorer convict five of eight
human documents in its own repository, which is documented rather than hidden.

Then it rewrites in two passes, stripping the tells first and rebuilding toward
an expert register second, and verifies the result: `--fidelity` inventories the
figures, names, quotes and stated feelings in your source and fails the rewrite
if any went missing or any appeared that was not there before.

## the numbers

Fifty AI-typical drafts, six genres, judged blind on shuffled labels. Pooled
over 100 verdicts, Zero Slop takes 55 best-picks against blader/humanizer 40,
no-ai-slop 5, de-slop 0. It wins the plurality against a 25% chance rate
(p = 1.7e-10) and is statistically tied with blader head to head (p = 0.15),
which is worth stating because most tools in this category would not.

A discrimination test separates obvious slop from obvious human writing across
five genres by 77 points, AUC 1.000. On ordinary human prose the false-positive
rate is zero of five, down from five of eight after two scoring bugs were found
by measurement. It runs at about 1,100 documents a second.

Every one of those numbers rests on corpora the author wrote, which is stated
plainly wherever they appear. They show the meter agreeing with an obvious
judgment, not that it generalises, and a defensible accuracy figure needs a
labelled corpus at volume that does not exist yet. That corpus is the top item
on the roadmap, ahead of the research-backed stylometric channels
(function-word bigrams and sentence-length distribution, per NEULIF
arXiv:2511.21744) that depend on it for calibration.

## the honest weakness

In the benchmark, Zero Slop ranked last of four on judge-rated fidelity and
carried the only fabrication flag: a rewrite invented a feeling the author never
described. Nothing in the loop measured fidelity, so the property the tool
claims to protect was enforced by instruction alone. The `--fidelity` channel
exists because of that and now catches the mechanical half — invented figures,
names and stated feelings — while a reframed claim still needs the judgment
pass. Publishing the result that went against it is the reason to trust the ones
that did not.

## it learns from your edits

The most honest signal a linter can get is what you change after it hands the
draft back. A span becomes a new pattern only after three independent documents
cut it, and a pattern you overrule three times loses half its weight, so the
meter sharpens in both directions with use. Reflection data stays on your
machine; sharing upstream is opt-in and carries spans and counts, never source
text.

---

MIT · [github.com/manavmishra/ZeroSlop](https://github.com/manavmishra/ZeroSlop)
· 58 tests · builds on no-ai-slop, humanizer, de-slop and stop-slop, Wikipedia's
Signs of AI writing, Kagi's SlopStop, and the detection literature cited in the
repository.
