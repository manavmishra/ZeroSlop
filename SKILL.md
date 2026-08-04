---
name: zero-slop
license: MIT
compatibility: Works in any Agent Skills-compatible harness (Claude Code, Codex, OpenCode, etc.). The statistical scorer uses python3 (stdlib only) and is optional — the skill degrades gracefully to its reference lists and self-rubric without it.
metadata:
  version: "1.2.0"
  author: manavmishra
description: Turn any draft — LinkedIn post, article, blog, newsletter, tweet, email, research abstract — into prose that reads as written by a sharp human, verified by a statistical scorer with before/after metrics (the only de-slop skill with a quantitative gate). Use whenever the user asks to humanize, de-slop, "make this not sound like AI", remove AI slop, fix a draft that "reads like ChatGPT", polish outward-facing writing, or draft social/LinkedIn content; also run it as a quality gate on prose you generated yourself before presenting it. Detects with a statistical scorer, rewrites by an evidence-ranked ladder, verifies against quantitative thresholds, and learns new tells over time.
---

# Zero Slop

A linter for the AI accent. The things that make prose read as machine-written
are measurable, so measure them, fix them, and show the numbers.

The science in one paragraph: detectors (and readers) key on the *post-training
register* — text that sits at the most-probable phrasing, with uniform sentence
rhythm, a few hundred over-represented style words, tidy template structure, and
relentless even polish. Every one of those signals lives in the surface
realization of the text, which means every one is removable while preserving
meaning exactly. `references/evidence.md` has the citations; the ladder below is
ordered by measured signal strength, strongest first.

## Hard rules (non-negotiable)

1. **Fidelity.** Meaning, claims, and facts survive exactly. Never invent a
   number, name, anecdote, or experience — and experiential/interior claims
   count ("by test day it felt familiar", "I was terrified"): if the author
   didn't say it, it's fabrication, even when it would make the piece land
   better. Specificity without source grounding is fabrication — worse than
   the slop it replaces.
2. **Flag hollow spans, don't fill them.** Prose that makes no claim cannot be
   rescued by rewording. Flag it and ask for the missing substance.
3. **No over-correction.** Trading AI-slop for edgy-slop (forced hot takes,
   fake first person, performed candor, staccato drama) is failure. Read
   `references/overcorrection.md` before heavy rewrites.
4. **Idempotence.** Text that already reads human returns unchanged. The best
   edit is often small.
5. **Honest use.** This skill improves writing quality and voice. Refuse
   requests to defeat AI-disclosure requirements (schools, journals, employers
   that require disclosure) or to impersonate a named individual.

## The loop

### 0. Scope

Identify: platform/genre (LinkedIn? blog? email?), audience, and what voice
evidence exists (user's past writing in the conversation, a stored voice
profile in `data/voices/`, or none). Skip code blocks, quotes, and legal
boilerplate. Take a form inventory: decide which parts of the document are
running text and which are legitimately structured (lists, tables, code,
diagrams, spec blocks), then hold each part to its own standard — the goal
is text a human would have written *in that form*, never prose-ifying
structure or structuring prose. If the genre matches any module in
`references/platforms.md`
(LinkedIn, X, email, blog, newsletter, research/professional), read it —
platform tells and overrides differ, and the research module *forbids* moves
the general ladder prescribes.

### 1. Measure

Run the statistical scorer on the draft:

```
python3 <skill-root>/scripts/slopscore.py --explain <file>   # any cwd; or pipe via stdin
```

Every channel runs on every draft: the pattern meter (68 weighted tells plus
a 72-term lexicon), rhythm and burstiness, followability, formatting
densities, and register. Each one is interpretable, so every point of the
score can be traced to a quoted span.

Add `--formal` for research/professional genres — it zeroes the
rhythm-uniformity and formality penalties, which would otherwise penalize a
register that is native there. If `python3` is unavailable in this
environment, skip the scorer and use `references/tells.md` plus the step-4
self-rubric as the gate — never fail the task over a missing interpreter.

Record the baseline: AI-likelihood (0–100), burstiness (sentence-length CV),
tell density, and every hit. The score is a surface meter, not a verdict — a
clean score with hollow content is still slop, and one flagged word in honest
technical prose is not. Clusters convict; singles don't.

### 2. Diagnose

Per paragraph, three judgments the regex cannot make:

- **Claim check (removal test):** delete the paragraph mentally — is anything
  lost? Nothing lost → *hollow* → flag, don't rewrite.
- **Facts inventory:** list every number, name, date, and quote. These survive
  the rewrite verbatim.
- **Voice signals:** note 3–5 things that are genuinely this writer's (cadence,
  humor, bluntness, pet phrases, digressions). These survive too. A user
  writing sample outranks every style rule in this skill.

### 3. Rewrite — the evidence ladder, in two passes

Run the ladder as two separate passes with different mindsets — benchmarking
showed a strip-then-build sequence beats one do-everything rewrite, because
each pass keeps a single focus. **Pass 1 — Strip** (subtraction only): L5
lexicon and L6 formatting, plus scaffolding removal. Touch nothing else; you
are deleting, not writing. **Pass 2 — Build** (on the stripped text): L1
substance, L2 order, L3 rhythm, L4 register — now you are writing, with the
tells already gone so nothing masks the substance judgments. The register
you are building toward is an **expert voice**: a respected practitioner
writing for peers — precise terms used correctly and unexplained, judgment
stated with earned authority, the confidence to be plain. Not clean-generic,
not casual-for-casual's-sake: the voice of someone who knows the field well
enough to say the simple true thing.

Expert also means **followable**. Density has a ceiling: one idea per
sentence; every abstraction gets a concrete anchor in the same breath; never
stack three or more abstract noun phrases in one sentence ("phrasing at the
probability maximum, uniform rhythm, template structure, relentless polish"
is compression, not writing — a reader can't hold five abstractions at
once). Lead the reader through the argument; if a smart first-time reader
would need to re-read a sentence, unpack it into two.

Guard against over-cutting in Pass 1: stripping is not compression. If a cut
costs warmth, flow, or a human aside, restore the connective tissue in Pass
2 — judges consistently mark "surface-clean but clipped" below "warm with one
leftover tell". Density is information per word, not fewer words.

Work each pass top-down; the top rungs carry the most detection signal and
the most reader value. `references/rewrite-moves.md` expands each rung.

- **L1 — Substance.** Replace generic abstraction with the specific thing:
  exact figures, named tools, the mechanism, the mistake. Commit to the claim
  the evidence supports; a sentence someone could disagree with is the
  strongest human tell. (Attacks predictability — the #1 detector feature.)
- **L2 — Order.** Break the template (definition → three points → summary).
  Lead with the most interesting claim. Let structure follow the argument.
- **L3 — Rhythm.** Vary sentence length hard: some under 8 words, some over
  30. Uneven paragraphs. One-line paragraph where the point lands. Target
  burstiness ≥ 0.45.
- **L4 — Register.** Break the uniform polish: contractions, spoken phrasing
  (the read-aloud test — rewrite anything you wouldn't say), calibrated hedges
  only ("I doubt this generalises" yes, "it's worth noting" no), real affect
  range including irritation and doubt. De-nominalize: "made a decision" →
  "decided". Kill participial openers ("Leveraging X, …").
- **L5 — Lexicon & patterns.** Strip the tell vocabulary and constructions —
  the scorer's hit list plus `references/tells.md`. Replace with plain words,
  never equally pompous synonyms. At most one "not X, it's Y" per piece; usually
  zero.
- **L6 — Formatting.** Em-dashes ≤1 per ~150 words (LinkedIn: zero). No bold
  spam, no emoji bullets, no hashtag clusters, no headers over two-sentence
  sections, bullets only where a list is truly a list.

### 4. Verify — quantitative gate

Re-run the scorer. The rewrite passes only when ALL hold:

- AI-likelihood ≤ 25 (transactional email: ≤ 35; research/professional
  genres: score with `--formal` and gate on tell density ≈ 0 plus zero
  high-weight hits instead — the composite penalizes formal register itself)
- burstiness ≥ 0.45 (texts ≥ 8 sentences; waived where the platform module
  relaxes rhythm rules)
- zero high-weight hits (weight ≥ 4) remaining, unless documented as the
  writer's own voice
- fidelity: every inventoried fact present and unchanged; nothing added the
  author didn't supply
- unsourced statistics: when the draft asserts a figure with no source ("~70%
  of pilots fail"), keep it as the author's own claim and flag it in the
  report. Never attach a citation the author didn't give, and never launder
  it into "studies show" — inventing attribution is fabrication, and weasel
  attribution is a tell
- source scope: every stat sits next to the source it actually came from,
  and a setup that names N sources pays off all N ("the number in two new
  reports is 6x" followed by only one report reads amnesiac — either scope
  the claim to its one source or give each named source its own number)
- self-rubric: survives a hostile editor's red pen; for opinion genres
  (LinkedIn, essays), ≥ 3 claims a reader could disagree with, drawn from the
  author's material — if the draft contains none, flag per step 5 rather than
  manufacture stance
- read-aloud pass: no sentence you'd stumble over or never say
- expert-voice test: would a respected practitioner in this field assume a
  peer wrote it? Terms precise, authority earned by specifics (never by
  adjectives), nothing dumbed down, nothing hedged into mush
- followability: a smart reader outside the field follows every sentence on
  the first pass, read aloud. The scorer's followability penalty must be
  ≈ 0 — comma-chained noun-phrase lists, long-word pileups, and 38+-word
  sentences are machine-compression tells, and "technically clean but
  exhausting" fails this gate even at a low composite score
- form follows context: not everything is prose. A checklist stays a
  checklist, a table stays a table, a diagram or spec block keeps its
  notation — the test is always "which form would a skilled human author
  choose for this content, in this genre?" But running text is prose: no
  arrow notation ("scores → 0–100"), no threshold dumps, no parameter
  lists posing as sentences. Where the form is structured, make it a good
  structure; where it is a sentence, make it read like a person wrote it
- whole-document consistency: the gate applies to the entire document at
  one register, including sections the edit didn't touch. A fixed paragraph
  next to an unfixed one fails. Cross-references must resolve exactly — if
  the text says "the ladder below," a section named the ladder must exist
  below, under that name

Fail → iterate (max 3 passes). Still failing after 3 → keep the best version
and flag it: "needs a real claim/detail, not better words."

### 5. Report

Every run ends with the rewritten text plus a **before/after scorecard** the
user can read at a glance — this is the product's proof and it is never
optional. Use this exact shape (a markdown table in chat contexts; the same
fields in plain lines where tables don't render):

```
| Metric                    | Before        | After        |
|---------------------------|---------------|--------------|
| AI-likelihood             | 45.7 suspect  | 9.5 clean ✓  |
| Weighted tells            | 6             | 0            |
| Em-dashes / emoji / tags  | 0 / 1 / 3     | 0 / 0 / 0    |
| Burstiness (≥0.45)        | 0.65          | 0.67         |
| Followability penalty     | 4.2           | 0            |
| Words                     | 254           | 217          |
Gate: PASSED (LinkedIn ≤20) · facts preserved 12/12 · nothing invented
```

Follow the scorecard with: (a) a short change log naming the patterns fixed
and the judgment calls made (including deliberate keeps); (b) flags — hollow
spans, capped spans, and anything needing a real fact from the user. Never
silently overwrite; the author decides.

### 6. Learn

This skill improves with use. When any of these happen, persist it:

- **New tell spotted** (a pattern readers call out as AI that the scorer
  missed) → add a regex + weight to `data/learned.json` (same schema as
  `data/patterns.json`; the scorer merges it automatically) and log one line
  in `data/learned-log.md` with the date and the example.
- **Never tune to pass the draft in front of you.** Weight changes are for
  patterns that misfire across *many* texts, and they get logged with the
  examples that motivated them. Lowering a weight because this draft failed
  is self-dealing, not learning, and it corrupts every future run.
- **False positive** (the scorer flags honest prose repeatedly) → for
  lexicon terms, re-add the term in `data/learned.json` with a lower weight
  (lexicon entries override the base); for regex patterns, lower the weight
  directly in `data/patterns.json` — learned patterns append, they cannot
  override. Log either change.
- **User voice feedback** ("I'd never say X", "keep my Y") → append to that
  user's profile in `data/voices/<name>.md`; read it at step 0 next time.
- **Era shift** — the lexicon moves as models change (delve peaked 2023–24;
  2025+ models over-use "emphasizing/enhance/highlight/showcase"). When new
  research or observation shows a shift, update weights rather than only
  adding words.

## References

- `references/tells.md` — the master taxonomy (67 tells, 6 families) with fixes.
- `references/rewrite-moves.md` — the positive program: the six ladder rungs
  expanded, with before/after pairs and voice calibration.
- `references/platforms.md` — LinkedIn, X/Twitter, email, blog, newsletter,
  research modules. Read the matching one whenever genre is known.
- `references/overcorrection.md` — edgy-slop catalogue, what NOT to flag, and
  the signs of human writing to preserve.
- `references/evidence.md` — the research basis: papers, detector mechanics,
  and why each ladder rung is ordered where it is.

## Worked example (LinkedIn)

**Before (AI-likelihood 100):**
> 🚀 I'm beyond excited to announce that after 18 months of hard work, we've
> raised $4.2M to transform how teams ship software! This wasn't just a
> milestone — it's a testament to our incredible team. Here are 3 lessons I
> learned along the way… Agree? 👇

**After (AI-likelihood 9.5):**
> We raised $4.2M. It took 18 months, and for the first six of them the demo
> crashed on stage more often than it ran.
>
> Basis Ventures led. The pitch that finally worked wasn't the vision slide.
> A customer told them our flag rollbacks saved his Black Friday, and that
> did more than I ever did.
>
> Six of us. Hiring two more. The bar: you've shipped something you were
> scared to ship.

Same facts. No invented ones — the crash detail and customer story came from
the author, which is the point: when specifics are missing, ask for a real one
(step 5 flags), never manufacture it.
