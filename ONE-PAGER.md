# Zero Slop

**A linter for the AI accent.** Scores a draft, strips the tells, proves the fix.

## The problem

Two 2024 studies caught it in the data. Stanford found "meticulous" appearing in
AI-conference peer reviews at nearly 35 times its pre-ChatGPT rate. Tübingen
found the same class of words surging across fifteen million biomedical
abstracts. Readers learned the accent fast enough that an em-dash on LinkedIn
now gets a writer accused of outsourcing their thinking.

Strip a model's assistant training and detectors call the raw output human 97 to
99 percent of the time. The accent is a style acquired in post-training. It
lives in wording, not ideas, which is why a careful rewrite can remove it
without altering a fact.

## The product

An agent skill that measures a draft, rewrites it in two passes, and reports
before-and-after scores. It runs offline with no dependencies, follows the Agent
Skills standard, and installs into Claude Code, Cowork, Codex, ChatGPT, Cursor
and anything else that reads skills.

Every run returns three things: the rewritten text, a scorecard, and a heatmap
showing which sentences carried tells.

## A real run

A founder's LinkedIn draft opened with "Enterprise AI value has too often
compounded inside individual workflows…" and scored **45.7 — suspect**, despite
having no emoji and no buzzwords. The catches were judgment calls: announcement
voice in the opener, the best statistic buried in paragraph two, and a hook
promising two reports while citing one.

The rewrite opens "Six times. That's how much more your best people talk to
models than everyone else does," gives each report its own number, and scores
**9.5 — clean**. Same facts, same citations, nothing invented.

## The evidence

Fifty AI-typical drafts, six genres, blind judges on shuffled labels, every
skill running its own published prompt.

Run one gave Zero Slop 32 of 50 best-picks. A replication with fresh judges on
identical texts gave 23. Cohen's kappa 0.12 means judges barely agree on "best",
so single-run numbers in this category are noise. Pooled across 100 verdicts:
Zero Slop 55, blader/humanizer 40, no-ai-slop 5, de-slop 0. That wins the
plurality against a 25 percent chance rate (p = 1.7 × 10⁻¹⁰) and is
statistically tied with blader head to head (p = 0.15).

The computed measures are steadier. Zero Slop leaves a detector score of 9.5
against 17 to 40 for the alternatives, a followability penalty of zero, and the
original's word count. Every other method shrinks the draft by up to 28 percent.

## The rules

No invented numbers, names, anecdotes, or feelings. Hollow paragraphs get
flagged, never padded. Performed candor and forced hot takes are rejected as the
louder dialect of the same disease. Where disclosure is required, disclose.

## Trust

The scorer is two hundred lines of standard-library Python. No network calls, no
dependencies, no accounts. Drafts never leave the machine, and personal voice
profiles are git-ignored.

## Install

```bash
npx skills add manavmishra/ZeroSlop --global
```

Or `/plugin marketplace add manavmishra/ZeroSlop` then `/plugin install
zero-slop@zero-slop` in Claude Code and Cowork. Then say "de-slop this."

---

github.com/manavmishra/ZeroSlop · MIT · builds on petergyang/no-ai-slop,
blader/humanizer, isatimur/de-slop, hardikpandya/stop-slop, Wikipedia's Signs of
AI writing, and fifteen detection papers cited in the repo.
