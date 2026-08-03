---
name: zero-slop
description: Turn any draft — LinkedIn post, article, blog, newsletter, tweet, email, research abstract — into prose that reads as written by a sharp human, verified by a statistical scorer with before/after metrics (the only de-slop skill with a quantitative gate). Use whenever the user asks to humanize, de-slop, "make this not sound like AI", remove AI slop, fix a draft that "reads like ChatGPT", polish outward-facing writing, or draft social/LinkedIn content; also run it as a quality gate on prose you generated yourself before presenting it. Detects with a statistical scorer, rewrites by an evidence-ranked ladder, verifies against quantitative thresholds, and learns new tells over time.
---

# Zero-Slop

Make writing read like a person wrote it — because the things that make prose
read as AI are measurable, and the fix is a rewrite, not a disguise.

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
boilerplate. If the genre matches any module in `references/platforms.md`
(LinkedIn, X, email, blog, newsletter, research/professional), read it —
platform tells and overrides differ, and the research module *forbids* moves
the general ladder prescribes.

### 1. Measure

Run the statistical scorer on the draft:

```
python3 <skill-root>/scripts/slopscore.py --explain <file>   # any cwd; or pipe via stdin
```

Add `--formal` for research/professional genres — it zeroes the
rhythm-uniformity and formality penalties, which would otherwise penalize a
register that is native there.

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

### 3. Rewrite — the evidence ladder

Work top-down; the top rungs carry the most detection signal and the most
reader value. `references/rewrite-moves.md` expands each rung with examples.

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
- source scope: every stat sits next to the source it actually came from,
  and a setup that names N sources pays off all N ("the number in two new
  reports is 6x" followed by only one report reads amnesiac — either scope
  the claim to its one source or give each named source its own number)
- self-rubric: survives a hostile editor's red pen; for opinion genres
  (LinkedIn, essays), ≥ 3 claims a reader could disagree with, drawn from the
  author's material — if the draft contains none, flag per step 5 rather than
  manufacture stance
- read-aloud pass: no sentence you'd stumble over or never say

Fail → iterate (max 3 passes). Still failing after 3 → keep the best version
and flag it: "needs a real claim/detail, not better words."

### 5. Report

Return: (a) the rewritten text; (b) before → after metrics (AI-likelihood,
burstiness, hit count); (c) a short change log naming the patterns fixed;
(d) flags — hollow spans, capped spans, and anything needing a real fact from
the user. Never silently overwrite; the author decides.

### 6. Learn

This skill improves with use. When any of these happen, persist it:

- **New tell spotted** (a pattern readers call out as AI that the scorer
  missed) → add a regex + weight to `data/learned.json` (same schema as
  `data/patterns.json`; the scorer merges it automatically) and log one line
  in `data/learned-log.md` with the date and the example.
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
