# Outreach kit

Copy for the placements that actually distribute a tool in this category, and
a record of what has been sent. Each block names where it goes, what the host's
stated bar is, and what has to be true before sending.

Sent on 30 August: both directory PRs, and issues to the two ancestor projects
that appear in the benchmark. Still to send: console.dev, Show HN, Reddit.

Score this file before changing it:

```bash
python3 scripts/slopscore.py --explain growth/outreach-kit.md
```

Sequence matters more than volume. Reciprocal links and the small directories
come first because they cost nothing and need no traction. Show HN and the large
lists come after the repository can survive the click: a visitor who lands on a
13-star repository from a big list bounces, and the slot is spent.

---

## 1. Reciprocal links from the ancestor projects

**Status, 30 August: two sent, two held.** The audit assumed these were
one-line PRs into an existing related-projects list. None of the four repos has
such a section, so a PR would have to invent one in someone else's README while
promoting a competitor. That is the shape maintainers reject, and this is a
small community Zero Slop depends on.

What was sent instead: an issue to each of the two projects that appear in the
replay benchmark, leading with **their own results** and an invitation to
dispute them, with the link request last and explicitly optional.

| Repository | Stars | In the benchmark | Action |
|---|---:|---|---|
| [blader/humanizer](https://github.com/blader/humanizer) | 38,903 | Yes, 35.4 | Issue [#250](https://github.com/blader/humanizer/issues/250) |
| [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) | 6,459 | Yes, 28.4 | Issue [#45](https://github.com/petergyang/no-ai-slop/issues/45) |
| [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | 16,583 | Capability chart | Issue [#64](https://github.com/hardikpandya/stop-slop/issues/64) |
| [isatimur/de-slop](https://github.com/isatimur/de-slop) | 2 | Capability chart | Issue [#18](https://github.com/isatimur/de-slop/issues/18) |

**How the last two got unblocked.** They were held because there was nothing to
bring them: credited in the README but absent from both the replay and the
capability chart, so the only possible message was "please link to me", which
is what makes maintainers close issues unread.

The fix was to make the finding rather than wait for one. The README credited
six projects and the chart audited four, which was the wrong way round anyway.
Auditing both against the same sixteen capabilities takes no model runs and no
budget, only reading their repositories at a pinned commit — and it produces
something they actually want, which is a claim about their project that they
can correct. de-slop came out as the most capable of the six after Zero Slop,
with five native, and that is the honest result rather than a courtesy.

The general move, if you need it again: when you have nothing to offer a
project, look for something true about them that nobody has written down yet.
An audit they can dispute beats a favour they have to grant.

The general shape that worked, if you extend this later: give them something
first, make the ask last, and say plainly that no is fine.

## 2. Small directories

**Both sent on 30 August.**

- [shannhk/avoid-slop](https://github.com/shannhk/avoid-slop) (177 stars) — PR
  [#2](https://github.com/shannhk/avoid-slop/pull/2). This list does not use
  bullets: every entry is a section with a blockquote, an install line, two or
  three paragraphs on what is distinctive, and a row in the Comparison table.
  A one-line entry would have been rejected on format alone. Placed last in
  Writing rather than against their roundup ordering.
- [hwajongpark/awesome-slop](https://github.com/hwajongpark/awesome-slop) (5
  stars) — PR [#5](https://github.com/hwajongpark/awesome-slop/pull/5), one
  line in *Fix it: humanizers*, with an offer to add the linters line too.

Both entries were scored before submission: 14.1 and 11.0, no flagged phrases.
Match the house format before writing the copy — that mattered more here than
the wording did.

---

## 3. console.dev — free editorial review

[console.dev](https://console.dev/) reviews 2-3 developer tools a week for
~22,000 developer subscribers. It does **not** run sponsored reviews, so the
only way in is the free submission, and its stated criteria fit:

- primary user is a developer — yes, it installs into a coding agent
- self-service, no sales call — yes, one command
- part of a regular-use toolchain — yes, it gates a docs build

Submit at [console.dev/selection-criteria](https://console.dev/selection-criteria).
Lead with the CI use, not the humanizing use: `slopscore.py --batch drafts/
--gate 25` fails a build above the threshold, which is the framing that reads as
a devtool rather than a writing app.

---

## 4. awesome-claude-code — hold, then resubmit

53,214 stars, and the single highest-value list in the ecosystem. Issue #2638
was opened 26 August and closed the next day with no comment.

Their contributing guide sets the bar plainly: **100 stars, or 14 days old with
continued active development.** It also says, in as many words, that submitting
before having users is the wrong order.

**Do not resubmit yet.** Resubmit after clearing 100 stars, and note that:

- submissions must use their web issue form; the `gh` CLI is explicitly refused
- one resource per submission
- [the form](https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml)

---

## 5. Show HN

Post only after the ancestor links and directories are live, so a visitor
arriving cold finds corroboration rather than a bare repository.

**Title:** `Show HN: Zero Slop – score your writing 0-100 for AI slop, then edit it out`

**First comment:**

> I kept asking models to fix AI-sounding drafts and getting back something
> worse: the vocabulary flattened, the rhythm went, and numbers quietly changed.
>
> Zero Slop is an Agent Skill rather than a model. It ships a standard-library
> Python scorer that gives a draft a 0-100 writing score and names the phrases,
> rhythm and formatting behind it. Your own assistant does the editing across
> separate passes, and a local fact gate rejects any rewrite that adds or drops
> a name, number, quotation or link.
>
> On an 18-draft benchmark rerun against avoid-ai-writing, no-ai-slop and
> humanizer — same model, same drafts, each tool's own pinned instructions —
> mean writing score went 76.3 to 12.8 with 18/18 fact checks passing. Drafts,
> mappings, verdicts and hashes are in the repo so it can be rerun.
>
> Two things it deliberately is not: an authorship detector (the score describes
> writing, not who wrote it), and a service (the scorer runs offline, no account,
> zero dependencies).
>
> Benchmark: https://zero-slop.ai/benchmark/

Lead with the reproducible number. HN rewards a benchmark someone can attack and
punishes marketing adjectives.

**Reddit:** r/ClaudeAI and r/LocalLLaMA take the same body with the title
`Scored 7,627 model generations for "AI slop" — here's what the numbers look like`,
leading with the RAID+ table rather than the install.

---

## 6. Newsletters, paid

See `growth/newsletter-analysis.md` for the cost model. Short version: not yet.
At 13 stars a paid click lands on a repository with no social proof, and the
star count is itself the conversion signal. Free editorial placement
(console.dev) first; paid only after the repository can hold a cold visitor.
