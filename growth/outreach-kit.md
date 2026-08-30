# Outreach kit

Ready-to-send copy for the placements that actually distribute a tool in this
category. Nothing here has been sent. Each block names where it goes, what the
host's stated bar is, and what has to be true before sending.

Score this file before changing it:

```bash
python3 scripts/slopscore.py --explain growth/outreach-kit.md
```

Sequence matters more than volume. Reciprocal links and the small directories
come first because they cost nothing and need no traction. Show HN and the large
lists come after the repository can survive the click: a visitor who lands on a
13-star repository from a big list bounces, and the slot is spent.

---

## 1. Reciprocal links from the four ancestor projects

The README credits these projects. They hold roughly 62,000 stars between them
and none of them link back. A maintainer accepts this when the crediting is
already mutual and the PR is small.

| Repository | Stars | Where to add |
|---|---:|---|
| [blader/humanizer](https://github.com/blader/humanizer) | 38,893 | Related projects / README footer |
| [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | 16,581 | Related projects |
| [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) | 6,458 | Related projects |
| [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | — | Related projects |

**PR title:** `Add Zero Slop to related projects`

**PR body:**

> Zero Slop credits this project in its README as prior work it builds on, so
> this adds the link in the other direction.
>
> Zero Slop is an MIT Agent Skill that scores prose 0-100 with a local,
> dependency-free Python scorer, then edits against a fact gate that rejects any
> rewrite changing a name, number, quotation or link. It runs the same
> before-and-after benchmark across several of these tools, including this one,
> and publishes the drafts, mappings and hashes so the comparison can be rerun.
>
> Happy to drop this if related-project links are not something you want in the
> README.

**One-line entry:**

```markdown
- [Zero Slop](https://github.com/manavmishra/ZeroSlop) — scores prose 0-100 and edits it against a fact gate. MIT, offline, zero dependencies.
```

---

## 2. Small directories, submit now

Neither of these needs traction, and both exist to list exactly this.

**[shannhk/avoid-slop](https://github.com/shannhk/avoid-slop)** (177 stars) — "a
curated directory of open-source tools for eliminating AI-generated slop". Open
a PR adding Zero Slop to the text-tools section:

```markdown
- **[Zero Slop](https://github.com/manavmishra/ZeroSlop)** — Agent Skill that scores writing 0-100 for AI-sounding language, names the phrases behind the score, and rewrites them. A local fact gate rejects any version that adds or drops a name, number, quotation or link. Offline, zero dependencies, MIT.
```

**[hwajongpark/awesome-slop](https://github.com/hwajongpark/awesome-slop)** (5
stars) — same entry, tools section. Small, but it is an exact-match list and
costs one PR.

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
