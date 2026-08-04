<!--
Zero Slop — single-file bundle for ChatGPT, Codex, and any assistant that
takes pasted instructions or an uploaded knowledge file.

HOW TO USE
  ChatGPT / ChatGPT at Work : Project → Instructions → paste this file.
                              Or Custom GPT → Knowledge → upload this file.
  Codex                     : save as AGENTS.md in your project.
  Anything else             : paste it. It is self-contained.

The statistical scorer needs a shell and is not included here. With Code
Interpreter enabled you can also upload scripts/slopscore.py from the repo to
get the numbers; without it, the reference lists below are the gate.

GENERATED FILE — do not edit. Run scripts/build_bundle.py after changing
SKILL.md or anything in references/.

Source: https://github.com/manavmishra/ZeroSlop   MIT
-->



========================================================================
# FILE: SKILL.md
========================================================================

---
name: zero-slop
license: MIT
compatibility: Works in any Agent Skills-compatible harness (Claude Code, Codex, OpenCode, etc.). The statistical scorer uses python3 (stdlib only) and is optional — the skill degrades gracefully to its reference lists and self-rubric without it.
metadata:
  version: "1.4.0"
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
boilerplate. **Record the input format** — pasted text, .md, .docx, .pdf,
.html, .txt, a JSON field — because the output must come back in that same
format (step 5). Take a form inventory: decide which parts of the document are
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
a 54-term lexicon and 13 context-gated riders), rhythm and burstiness,
followability, formatting
densities, and register. Each one is interpretable, so every point of the
score can be traced to a quoted span.

Pass `--genre social` for LinkedIn and X, which switches on the shape channel
(paragraph structure and fragment runs). Genre comes from step 0, never from
auto-detection: nothing in the text separates a poem from broetry, but you
already know which one you are editing.

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
- shape (social genres only): the scorer reports `broetry` when most
  paragraphs are single sentences and fragments run three or more deep. This
  is its own axis, never folded into the score, because broetry is a slop tell
  rather than a machine tell — LinkedIn writers invented it years before
  GPT-3, and it demonstrably performs there. Report it and let the author
  decide whether reach is worth the voice
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

Every run ends with three things, in this order, and none of them is
optional: the **rewritten text**, a **before/after scorecard**, and a
**before/after heatmap**. Together they are the product's proof — the text is
the deliverable, the scorecard is the measurement, and the heatmap shows
*where* the slop was, which is what teaches the writer rather than just
fixing the draft.

**(a) The rewritten text**, in full, **returned in the format it arrived
in.** This is not a stylistic preference — a user who hands you a .docx wants
a .docx back, and pasting markdown into chat instead makes them do the
conversion by hand. Match the input:

| Input | Output |
|---|---|
| Pasted text in chat | The rewritten text in chat, same shape (paragraphs, line breaks, list structure preserved) |
| `.md` / `.txt` file | The same file rewritten in place, or a sibling `<name>-deslopped.<ext>` when the original must be preserved |
| `.docx` | A `.docx`, styles and structure intact (use the docx skill; never return markdown for a Word document) |
| `.pdf` | A `.pdf` rendered to match the original's layout and typography (use the pdf skill) |
| `.html` | `.html`, with the markup, classes and structure preserved and only the prose nodes touched |
| A file inside a repo | Edited in place, so the diff is reviewable |
| A field in JSON/YAML/CSV | The same structure with only that field's value rewritten |

Two rules that follow from this. **Preserve everything that is not prose**:
front matter, code blocks, tables, image references, links, IDs, merge
fields, and formatting all survive the rewrite untouched. And **never
silently downgrade the format** — if the environment genuinely cannot produce
the input type, say so plainly and hand back the closest thing, rather than
quietly returning markdown and letting the user discover the mismatch.

The exception is an explicit request: if the user asks for a different format
("give me this as plain text", "put it in a doc"), that instruction wins.

**(b) The scorecard.** Use this exact shape (a markdown table in chat; the
same fields as plain lines where tables don't render):

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
Checked: vocabulary, formatting, rhythm, followability, register, shape
Not measured: substance, voice, factual accuracy
```

**Never print a bare PASS.** The gate covers the channels it can compute, and
saying so is the difference between a verdict and a claim the tool cannot
support. A draft can be word-clean and still read as machine-written; when the
diagnose pass sees that, say it in the report even when every number is green.
A green number never means the judgment pass was optional.

**(c) The heatmap**, before and after, from
`python3 <skill-root>/scripts/slopscore.py --heatmap <file>`:

```
  SLOP MAP · 7 sentences · 5 carry tells · hottest first

  ████████  heavy    ¶1  "I'm beyond excited to"
                      LinkedIn tell — readers pattern-match this to AI instantly
  ███░░░░░  mild     ¶3  "Let's dive"
                      structural filler — delete the stem, keep the point

  by paragraph  █ · ▓ ▒   █ heavy  ▓ moderate  ▒ mild  · clean
```

Read it as: severity on an absolute scale (so bars mean the same thing in
every document), the paragraph it lives in, **the exact phrase that triggered
it**, and what to do instead in plain English. The paragraph strip at the
bottom shows where slop clusters, which is often more useful than any single
line — three heavy paragraphs and a clean one tells you the piece has a
structural problem, not a word problem.

The after-map should read `none carry tells`. Show both. A writer who sees
which phrases were hot stops producing them, and that outlasts the rewrite.

Then close with: a short **change log** naming the patterns fixed and the
judgment calls made, including deliberate keeps; and **flags** — hollow
spans, capped spans, and anything needing a real fact from the user. Never
silently overwrite; the author decides.

### 6. Learn

This skill improves with use, and the strongest signal is the writer's own
edit. If you hand back a rewrite and the author changes something before
publishing, that change is a free label: what you left in that a human took
out was a tell you missed. Capture it.

- **The reflect loop.** Whenever you can see both what the skill produced and
  what the author actually shipped — they paste the final version, they say
  "I cut X", you edit a file they later revise — record it:

  ```
  python3 scripts/learn.py --reflect --produced out.md --shipped final.md
  ```

  This does **not** create a pattern. It records an observation. A span
  becomes a pattern only after it has been independently cut from three
  different documents, because a single diff cannot tell a stylistic tell
  from an author trimming a sentence for length. Once a span clears that
  bar, `--promote --apply` mints it, and the accuracy of the meter rises
  with the number of people using it rather than with anyone's guesswork.

  Three gates stand between an observation and a shipped pattern:
  recurrence (three distinct documents), novelty (not already scored), and
  safety (must not fire on, or borrow four consecutive words from, the
  certified human writing in `data/corpus/must-not-flag/`). The safety gate
  is absolute — a pattern that would convict Lincoln, an SRE runbook, or a
  non-native English speaker's email is rejected at any level of evidence.
  Learning that corrupts the meter is worse than not learning.

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
  2025+ models over-use "emphasizing/enhance/highlight/showcase"). Rather
  than guessing new weights, derive them:

  ```
  python3 scripts/calibrate.py --human <dir> --ai <dir>
  ```

  This computes each term's excess frequency in current AI output against
  known-human writing — the method the excess-vocabulary studies used — so
  the meter tracks the model generation you actually face. Point it at your
  own past writing for a personal baseline, or at this month's model output
  for an era refresh.

- **Every change is gated.** After editing patterns or weights, run

  ```
  python3 scripts/calibrate.py --selftest
  ```

  which scores a corpus of writing that must never be flagged
  (`data/corpus/must-not-flag/`, 12 samples): dash-heavy 19th-century oratory, dense
  technical prose, terse engineering notes, business memos, human press
  copy, and non-native English. A pattern that convicts any of them is
  rejected before it ships. Add a sample to that corpus whenever you find
  honest writing the meter got wrong — that is how a false positive becomes
  permanent protection rather than a one-time fix, and it is the most useful
  contribution anyone can make to this skill.

- **Context beats a global weight.** Terms that are ordinary technical
  vocabulary ("robust", "landscape", "elevated", "leverage") live in
  `riders` and only score when a marketing-register trigger shares their
  sentence. "Elevated write volume" in a runbook is silent; "elevate your
  brand with our seamless platform" is not. When a term proves
  context-dependent, move it to `riders` rather than lowering its weight
  globally.

- **Patterns carry provenance and decay.** Every pattern records
  `first_seen`/`last_confirmed`; `calibrate.py --decay` halves the weight of
  anything unconfirmed for 18 months, so a 2024 tell fades on its own instead
  of accumulating forever. The other half is re-earning weight:
  `learn.py --confirm <dir>` bumps `last_confirmed` on every pattern that
  fires against known slop, so a tell that keeps catching things stays sharp
  while one the models have moved past ages out by itself. Run
  `learn.py --stats` to see the taxonomy's age, sources, and what is pending
  promotion.

## References

- `references/tells.md` — the master taxonomy (61 tells, 6 families) with fixes.
  It is the human-readable catalogue; `data/patterns.json` is its machine
  implementation and carries 68 regexes, since some tells need more than one.
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


========================================================================
# FILE: references/tells.md
========================================================================

# The Tell Taxonomy

Sixty-seven tells in six families, merged from WP:AICATCH (Wikipedia's editor
catalog, built from thousands of caught instances), the de-slop/stop-slop
detector line, petergyang/no-ai-slop, blader/humanizer, and the academic
lexicon studies (Kobak, Liang, Juzek & Ward). The scorer
(`scripts/slopscore.py`) catches the lexically detectable ones; the rest need
judgment. **Clusters convict, singles don't** — one "robust" in technical prose
is nothing; five tells in one paragraph is a verdict.

## 1. Lexical

| Tell | Fix |
|---|---|
| AI vocabulary: delve, tapestry, testament, realm, intricate, interplay, landscape, meticulous, pivotal, garner, bolster, underscore, showcase, foster, boasts | Plain word or the specific thing. "delve into" → "look at"; "the AI landscape" → name the actual companies/tools |
| Marketing register: seamless, frictionless, cutting-edge, game-changer, state-of-the-art, supercharge, paradigm shift, empower | Delete or state the concrete capability |
| Rider buzzwords (leverage, robust, unlock, harness, streamline) | Fine in plain technical prose; slop when clustered with marketing words |
| Puffery: nestled, breathtaking, rich heritage, renowned, vibrant, groundbreaking | State the fact; let the reader judge importance |
| Legacy phrases: "a testament to", "pivotal moment", "enduring legacy", "evolving landscape", "setting the stage" | Say what happened |
| Copula avoidance: "serves as", "stands as", "functions as", "boasts", "features" | "is" / "has" |
| Stiff synonyms: utilized, authored, attempted, relocated | used, wrote, tried, moved |
| Vague quantifiers: "a wide variety of", myriad, plethora, countless, numerous | The number, or "many", or cut |
| Filler intensifiers: truly, genuinely, incredibly, undoubtedly | Cut; keep only when carrying real emphasis in the writer's voice |
| Degree intensifiers (very, really + adj) | Weak signal alone; cut in clusters |
| Business jargon: circle back, move the needle, low-hanging fruit, deep dive, double-click | The actual verb |
| 2025+ era shift: emphasizing, enhance, highlight(ing), showcasing now outrank delve | Same fix; keep `data/learned.json` current |

## 2. Structural

| Tell | Fix |
|---|---|
| Listicle stems: "There are several key factors…", "Here are 5…" | Make the first point; structure follows argument |
| "Not only X but also Y" | Pick the stronger of X/Y, state it |
| Dead transitions: Moreover, Furthermore, Additionally at sentence start | "but", "so", "and", or nothing — humans cohere with connective texture, not scaffolding |
| Wrap-up scaffolding: "In conclusion", final paragraph restating the piece | End on the last concrete point or consequence |
| Rule of three: "fast, reliable, and scalable" | Two items, or one, or an actual list with content |
| "Challenges and future prospects" formula | Delete the formula; report the one real challenge |
| Rigid outline: every paragraph topic-sentence + 3 supports + mini-conclusion | Reorder; let paragraph lengths vary; put the best claim first |
| Participial analysis tails: "…, highlighting the importance of X" | Full stop, then the actual consequence ("so users can…") or nothing |
| Inline-header bullet lists (• **Header:** text) | Prose, unless it's truly a list |
| Tiny tables for prose content | Prose |
| Transformation chains: "X becomes Y. Y becomes Z." | One plain causal sentence |
| Synonym cycling (the agent/the assistant/the tool for one referent) | Repeat the clear word |
| Stacked hedges: "might possibly", "could potentially perhaps" | One hedge or none |

## 3. Rhetorical

| Tell | Fix |
|---|---|
| Empty hedging: "It's worth noting that", "it's important to note" | Delete the stem; keep the content |
| Didactic disclaimers: "it's crucial to remember", "results may vary" | Delete unless a real caveat, then state it precisely |
| Manufactured stakes: "in today's fast-paced world", "now more than ever" | Start where the reader needs to start |
| Performed candor: "let's be honest", "here's the thing", "truth be told" | State the point |
| Rhetorical-question openers: "Ever wondered…?", "What if I told you…?" | The answer, as a statement |
| Throat-clearing: "The uncomfortable truth is", "Let me be clear" | Cut; the claim stands alone |
| Emphasis crutches: "Make no mistake", "Let that sink in", "Read that again" | Show the weight with the fact itself |
| Meta-commentary: "In this post we'll explore", "Let me walk you through" | Just do it |
| Corrective reveal: "You've been told X. Here's the truth" | Make the claim without the posture |
| Binary contrast reveal: "The answer isn't X. It's Y." | "Y matters more than X" — and at most once per piece |
| Negative parallelism family: "It's not just X, it's Y" / "No X. No Y. Just Z." / "It wasn't A. It wasn't B. It was C." | State the positive claim once |
| Forced profundity: "You can't have one without the other" | Earn it or cut it |
| Calls to action: "Buckle up", "Let's dive in", "Stay tuned" | Cut |
| Weasel attribution: "Experts agree", "Studies show", "Industry reports suggest" | Name the source or cut the claim; if no source exists, ask the author |
| Canned coverage claims: "featured in prominent media outlets" | Name the outlet and what it said |

## 4. Punctuation & formatting

| Tell | Fix |
|---|---|
| Em-dash overuse (density; 2+ in a sentence; spaced pairs as drama) | Commas, periods, parentheses; ≤1 per ~150 words; zero on LinkedIn |
| Title Case Headings everywhere | Sentence case |
| Bold spam mid-sentence | Unbold; if it needs emphasis, restructure |
| Emoji as bullets/headers (🚀 ✅ 👉) | Remove |
| Hashtag clusters | Zero in body; move to first comment if needed |
| Markdown artifacts in plain-text contexts | Strip |
| Chatbot markup leakage (oaicite, citeturn0…, [cite: 1], utm_source=chatgpt.com) | Strip — these are proof, not style |
| Placeholders left in ([Your Name], [Company]) | Fill or flag |
| Curly-quote inconsistency | Normalize to the document's convention |

## 5. Tone

| Tell | Fix |
|---|---|
| Assistant voice: "Great question!", "I hope this helps", "I'd be happy to" | Delete |
| Knowledge-cutoff residue: "as of my last update", "not widely documented" | Delete; verify the claim |
| Promotional drift in neutral contexts | Neutral statement of fact |
| Uniform flawless register (every sentence equally polished) | Vary: blunt next to careful, casual next to technical |
| Excess positivity, joy-skewed affect | Allow doubt, irritation, dry humor where genuine |
| Fake humanization (edgy-slop) | See `overcorrection.md` — it's still slop |

## 6. Content-emptiness (judgment only — no regex can see these)

| Tell | Test | Action |
|---|---|---|
| Hollowness — no claim at all | Removal test: delete it; anything lost? | Flag, never pad |
| Regression to the mean — specifics smoothed into generic + inflated importance | Compare against source facts | Restore the specific |
| Smooth-but-empty specificity — "modern technologies that ensure reliability" | Can you name the referent? | Name it or cut |
| Superficial analysis — unearned significance commentary | Who says it matters? | State the mechanism or cut |
| Fabricated support — invented citations, stats, anecdotes | Verify every reference | Remove; ask author for real one |
| Speculative gap-filling — "likely supports…" | Is there a source? | Cut or mark as open question |

## What is NOT a tell (do not flag)

Perfect grammar. Formal prose where the genre demands it. A transition word in
isolation. Long sentences that earn their length. Technical vocabulary used
technically. A single em-dash doing real work. First-person hedging that
encodes real uncertainty. Unsourced-but-checkable claims. And any pattern that
is demonstrably the writer's own voice — the writing sample outranks the list.


========================================================================
# FILE: references/rewrite-moves.md
========================================================================

# Rewrite Moves — the positive program

Removing tells makes text neutral. These moves make it human. Ordered by the
evidence ladder (L1 strongest detection signal + reader value).

## L1 — Substance: raise the information

The deepest difference between human and machine prose is measurable:
AI text sits at the most-probable phrasing (DetectGPT's log-prob curvature),
and the most-probable phrasing is the generic one. Specificity is the attack.

- **Commit to a claim.** Find where the draft goes vague to avoid committing,
  and commit. "AI can help teams work faster" → "The router cut our bill in
  half; the part nobody warns you about is quality drops too unless you gate
  it." Count claims a reader could disagree with — sloppy text has ~zero.
- **Concretize every generic noun phrase.** "various industries" → the two
  industries you mean. "significant improvement" → "340ms → 90ms".
  "stakeholders" → who. If you cannot name it, the sentence has no content —
  cut it or flag it.
- **Add only what the author actually has.** A real number, the client
  situation, what went wrong, why they stopped doing it the old way. This is
  the one move that cannot be faked — never invent it. If the material isn't
  in the source, ask (flag: "needs a real detail here").
- **Keep the odd, drop the round.** "$1.1M raised, 4,000 users" beats "over a
  million dollars and thousands of users." Preserve un-smooth facts; AI
  regresses them to the mean.
- **Density has a ceiling: stay followable.** Raising information per word
  fails when the reader can't absorb it. Caught in live use:
  "They detect the post-training register: phrasing at the probability
  maximum, uniform sentence rhythm, a few hundred over-represented style
  words, template structure, relentless even polish" — zero tells, and
  unreadable: five abstractions in one breath, nothing concrete to hold.
  The fix is unpacking, not dumbing down: "They catch a writing style, the
  one every chat model ships with after preference tuning. You know it when
  you read it: every sentence the same length, every word the safest
  choice, a polish that never varies." One idea per sentence. Anchor each
  abstraction in something the reader can hear or picture. The scorer's
  followability channel (comma-chains, long-word ratio, 38+-word
  sentences) measures this; the read-aloud-as-an-outsider test judges it.
  Beware the near-miss fix: swapping an abstraction-chain for an
  unexplained metaphor ("the AI voice is in the finishing school") moves
  the decoding load instead of removing it. A metaphor anchors only when
  its mapping is set up first; otherwise use the plain comparison the
  reader can picture ("take one model in two versions: raw, and after
  assistant training — detectors read the raw one as human"). Citation
  name-lists belong in the reference file, not the sentence.

## L2 — Order: break the template

Canonical LLM ordering (definition → three balanced points → summary) is
itself a tell, independent of wording (DIPPER showed reordering defeats
detectors as much as re-wording).

- Lead with the most interesting true sentence in the piece. It's usually
  buried in paragraph 3.
- Delete the intro that announces the topic and the outro that restates it.
- Let sections be unequal: the important point gets 60% of the words.
- If the piece argues, follow the argument. If it narrates, follow time.
  Never follow the essay template.

## L3 — Rhythm: engineer burstiness

Sentence-length variance is a top-tier detector feature and the easiest to
measure (the scorer reports it; target CV ≥ 0.45).

- After a 30-word sentence, a 4-word one. On purpose.
- One-line paragraph where the point lands. Once, maybe twice.
- Place the punchy register where it belongs: hooks and landings. An
  analytic middle paragraph built from stacked clipped declaratives reads
  robotic — the staccato costume of over-correction. Middles want flowing,
  subordinated sentences (think a good newspaper editor), saving the
  fragment for the moment it earns.
- Fragments, where they work. Starting with And or But is fine.
- Vary paragraph shape: a 6-sentence paragraph next to a 1-sentence one.
- Don't pad every claim to equal weight — humans spike information unevenly
  (dense sentence, then a breather). An abrupt claim without wind-up is human.

## L4 — Register: break the RLHF voice

Detectors flag instruction-tuned models' register, not machine text per se —
the uniformly polished, evenly hedged, affect-positive expository voice.
Breaking it matters more than any word swap.

- **Read-aloud test (Paul Graham).** Every sentence: would you say this to a
  friend? No → rewrite in the words you'd actually say. Contractions in;
  Latinate stiffness out ("utilize" → "use").
- **Hedge like a person.** People hedge selectively, where they're actually
  unsure: "I doubt this generalises past Postgres." Machines hedge everywhere
  equally: "it's worth noting that results may vary." One calibrated hedge
  beats five ceremonial ones; qualification should encode real confidence
  (How to Write Usefully).
- **De-nominalize.** "made an assessment of" → "assessed"; "provides
  optimization of" → "optimizes". Kill participial sentence openers
  ("Leveraging X, the system…" → "The system uses X to…").
- **Widen affect.** Allow irritation, doubt, amusement where genuine. AI
  affect is uniformly upbeat-neutral; one honestly grumpy sentence is worth
  ten vocabulary fixes.
- **Insider reference.** Name the specific tool, paper, failure mode.
  Explaining what an API is to engineers signals outsider; assuming shared
  knowledge signals membership.
- **Expert authority, earned.** The target voice is a senior practitioner
  writing for peers. Authority comes from specifics and correct technical
  usage, never from intensity ("truly transformative") or credentials
  waved around. An expert says the simple true thing plainly, states
  numbers exactly, disagrees where the field is wrong, and reserves hedges
  for the genuinely uncertain. If a sentence could appear in any
  competent generalist's post, it isn't expert voice yet.

## L5 — Lexicon: strip the tells

The lists live in `tells.md` and the scorer's data files. Two rules beyond
the lists:

- Replace with the *plain* word, never an equally pompous synonym ("delve
  into" → "look at", not "plumb the depths of").
- Budget the constructions that are fine once but damning in multiples: max
  one "not X, it's Y" per piece (usually zero), no tricolons on autopilot,
  no colon-reveals.

## L6 — Formatting: quiet the page

Format follows content. Em-dashes ≤1/150 words (LinkedIn: zero). No bold
spam, emoji bullets, hashtag clusters, headers over two-sentence sections, or
bullets where prose reads better. Normalize quotes. Strip markdown artifacts
and any chatbot markup leakage.

## Voice calibration

Never rewrite "in the user's voice" without evidence of the voice.

**With samples** (conversation history, linked posts, `data/voices/<user>.md`):
extract typical sentence length and variance; contractions y/n; first person,
questions, humor; punctuation habits; vocabulary level and jargon used
unexplained; how they open and close; what they push back on. Preserve the 3–5
strongest markers verbatim-level.

**Without samples:** ask for two paragraphs of their real writing — it beats
any description. If unavailable, ask three questions: who's the reader, what
should they do after reading, and what do you believe about this that peers
don't?

Store what you learn in `data/voices/<user>.md` so the next run starts warm.
A writing sample outranks every rule in this skill: if the user genuinely
writes with em-dashes and "honestly", those stay.

## Worked contrast

**Flat (says nothing, perfectly clean):**
> Model routing is an effective strategy for reducing AI costs while
> maintaining quality.

**Human (contains things):**
> We put a router in front of everything about eight months ago. The bill
> dropped by half, which everyone expects. What nobody warns you about is that
> quality drops too unless you gate it — we shipped three weeks without an
> eval gate and spent longer cleaning that up than the routing took to build.

Longer, but not padded: a date, a number, a mistake, and a warning that only
comes from having made it. That's the difference density measures.


========================================================================
# FILE: references/platforms.md
========================================================================

# Platform Modules

Genre changes which tells matter most and what "good" looks like. Read the
matching module at step 0. Rules here add to, and where noted override, the
general ladder.

## LinkedIn (the highest-slop environment on the internet)

LinkedIn AI slop has its own dialect on top of the general tells. Readers now
pattern-match it instantly; comments calling out "this is ChatGPT" are the
failure condition.

**Platform-specific tells (all high weight):**
- Announcement voice: "I'm excited/thrilled/humbled/proud to announce/share"
- Emoji bullets (🚀 ✅ 💡 👉), the 👇 pointer, emoji-decorated hooks
- Hashtag clusters in the body
- Engagement bait endings: "Agree?", "Thoughts?", "Drop a comment", "Repost
  if…", "Tag someone who…"
- Teaser hooks that withhold: "This changed everything for me…"
- "Here's what I learned" / numbered "Lesson 1:" scaffolding
- Broetry: every sentence its own line, staccato drama, "Read that again."
- Gratitude-journey register: "humbled", "grateful for this journey",
  "couldn't have done it without"
- Manufactured vulnerability: "Writing this is hard…", "with a heavy heart"
- The fake-profound kicker aphorism: "Failure isn't the opposite of success…"

**What works instead:**
- Hook = the claim or the number, line one, under ~12 words of wind-up.
  "Thirty-two cents." beats "I want to share something surprising about
  agent economics."
- First person, short declaratives, judgment first. One person talking.
- Concrete specifics: real numbers, named tools, the mistake. ≥3 claims a
  reader could disagree with.
- Zero em-dashes (the single most-cited LinkedIn AI tell). Zero hashtags in
  body (first comment if needed). No bolded name-drops.
- At most one credential line, and only a true one.
- Max one "not X, it's Y" (prefer zero). No tricolons on autopilot.
- Rhythm varies: long sentence, then a fragment. A one-line paragraph where
  the point lands.
- End on a direct question that a specific reader would actually answer, or a
  landing line. Links go in the first comment (reach), offered once.
- 150–250 words. Shorter beats longer.

**LinkedIn verify overrides:** scorer threshold ≤ 20; em-dash count = 0;
emoji = 0 (unless the author's samples genuinely use them); hashtags in body
= 0.

## X / Twitter

- Single tweets: the claim, plainly. No "🧵", no "a thread on…", no
  "1/12" ceremony unless genuinely a thread.
- Threads: each tweet must stand alone as a sentence someone would quote.
  Cut connective tweets ("But here's where it gets interesting…").
- No hashtag decoration; no "Let that sink in"; no engagement-farm endings
  ("What did I miss?", "Bookmark this").
- Fragments and lowercase are native here; formality is the tell.

## Email (marketing / transactional)

- Subject line: the concrete offer or fact, not curiosity-gap bait.
- One idea, one CTA. Delete warm-up paragraph; open with the reason you're
  writing. "I hope this email finds you well" is assistant-voice — delete.
- Bullets only for genuinely scannable facts (date, time, price).
- "Whether you're X or Y" audience-hedging, "Don't miss out", "spots are
  filling fast" (unless true and specific) — cut.
- Placeholders ([First Name]) must be filled or flagged.
- Constrained-format allowance: scorer threshold ≤ 35 is acceptable; brevity
  and template structure are native to the genre. Rhythm rules relax;
  fidelity and lexicon rules don't.

## Blog / article

- Kill the SEO-intro ("In today's digital landscape… In this article we'll
  cover…"). First paragraph must contain the piece's best fact or claim.
- Headers in sentence case, only above sections that need them (>2
  paragraphs). No "Conclusion" header restating the piece.
- The essay template (intro → 3 points → recap) is the tell; argue instead.
- Long-form earns digressions and asymmetry — use them. A personal aside
  the template would never produce is a human signature.

## Newsletter

- Segments should read like a person telling you what mattered, not a wire
  service: lead each item with the "so what", not the announcement.
- Cut "In this week's edition…" scaffolding; jump in.
- One editorial opinion per issue minimum — a newsletter with no judgment is
  a feed.
- Recurring-format elements (headers, dividers) are fine; identical *prose
  rhythm* across items is the tell.

## Research / professional documents (abstracts, exec summaries, whitepapers)

- Formal register is native; do NOT casualize. Contractions/fragments rules
  relax; the read-aloud test becomes "would a careful author write this?"
- The tells that remain deadly here: puffery ("novel", "comprehensive"
  unearned), copula avoidance ("serves as"), participial analysis tails,
  vague quantifiers replacing available numbers, hedge stacks, and the
  "Challenges and Future Directions" formula.
- Keep calibrated hedging — in research, uncertainty statements are accuracy,
  not filler. Cut only ceremonial hedges ("It is worth noting that").
- Numbers stay exact; never round for flow. Structure may legitimately be
  templated (IMRaD) — judge sentences, not the outline.


========================================================================
# FILE: references/overcorrection.md
========================================================================

# Over-correction — the second failure mode

The classic humanizer failure is swapping AI-slop for a louder slop. Readers
clock both. Everything here is a rewrite *output* ban: never introduce these
into text that didn't have them.

## The edgy-slop catalogue

- **Forced contrarianism** — "Everyone says X. They're wrong." (unless the
  source argued it)
- **Fake first person** — "I've seen this a hundred times", "In my
  experience…" injected into authorless prose. Manufactured war stories are
  fabrication, the cardinal sin.
- **Performed candor** — "Let's be real", "Here's the thing", "I'll be
  honest": candor is shown, not announced.
- **Staccato drama** — "This matters. A lot. More than you think." Broetry
  fragmentation is the LinkedIn variant.
- **Em-dash theatrics** — dashes manufacturing emphasis the content didn't
  earn. (Yes, humanizers add these; yes, it reads as AI.)
- **Binary-contrast reveals** — "The answer isn't more tools. It's
  discipline." One per piece max; injecting them is over-correction.
- **Manufactured stakes** — "In a world where…", "Now more than ever".
- **Intensifier padding as personality** — "genuinely", "honestly",
  "literally" sprinkled for flavor.
- **Slang costume** — forced colloquialisms a professional author wouldn't
  use ("chef's kiss", "hits different") unless the voice sample has them.
- **Fake errors** — never inject typos or grammar mistakes to fool
  detectors. That's adversarial evasion, not writing, and it degrades the
  text.

The bar is a *thinking* author, not a *loud* one.

## What NOT to flag (false-positive guard)

From Wikipedia's "ineffective indicators" plus detector-calibration
experience — these alone are NOT evidence of AI:

- Perfect grammar and spelling
- Formal or technical register where the genre demands it
- A transition word, an em-dash, a "however" in isolation
- Long sentences that earn their length
- Rule-of-three used once, deliberately, for rhythm
- Domain jargon used correctly for a domain audience
- Calibrated hedging in research/medical/legal writing
- Text merely being unsourced (check it, don't flag it)

Clusters convict. A paragraph needs multiple independent tells, or a failed
removal test, before it's slop.

## Signs of human writing — preserve on sight

When a draft shows these, protect them through the rewrite; deleting them is
damage:

- A claim someone could disagree with, stated without cover
- The specific odd fact ($1.1M, 4,000 users, "episode 142")
- Selective hedging at the edge of the author's knowledge
- Humor, irritation, dry asides, self-interruption
- Digressions that carry personality; asymmetric structure
- Insider references assumed, not explained
- The author's pet phrases and punctuation habits (voice sample rules)
- Mistakes of passion — a run-on in an excited passage. Leave it.

## Idempotence check

Run the finished rewrite through the scorer and this file once more. If your
rewrite added any catalogue item above, you traded costumes. Prefer the
smaller edit: the best de-slop is usually deletion of the hedge plus nothing.


========================================================================
# FILE: references/evidence.md
========================================================================

# Evidence Base — why the ladder is ordered the way it is

Every rule in this skill traces to measured findings. This file is the chain
of custody. Full dossier with per-paper notes lives in the research archive;
citations here are the load-bearing ones.

## The central finding

Commercial detectors (GPTZero, Pangram) rate *base-model* text as ~97–99%
human while flagging *instruction-tuned* output from the same model
(arXiv:2605.19516). Detectors are classifiers of the **post-training (RLHF)
register** — the polished, uniform, preference-optimized voice — not of
machine generation itself. That register lives entirely in surface
realization, which is why rewriting can remove it without touching meaning.
It is also why "humanizing" is legitimate editing: the target is a register,
not a deception.

## Detection features, ranked by evidence strength

1. **Token-level predictability.** AI text sits at local maxima of model
   log-probability (DetectGPT, arXiv:2301.11305; Binoculars, 2401.12070).
   Human text doesn't. → Ladder L1: specific, slightly surprising phrasing
   and concrete facts are the direct counter.
2. **The LLM lexicon.** A few hundred style words carry huge evidential
   weight: "meticulous" +34.7x, "commendable" +9.8x, "intricate" +11.2x in
   post-ChatGPT scientific text (Liang, 2403.07183); ~900 excess words
   catalogued across 15M PubMed abstracts (Kobak, 2406.07016 —
   github.com/berenslab/llm-excess-vocab); 21 focal words traced to RLHF
   (Juzek & Ward, 2412.11385). Era-dependent: delve peaked 2023–24;
   enhance/highlight/showcase dominate 2025+. → Ladder L5 + the scorer's
   weighted lexicon + the learning loop's era updates.
3. **Surprisal uniformity.** Humans spike information density unevenly; LLMs
   smooth it (GPT-who/UID, 2310.06202 — beats commercial detectors by >20%).
   → L3's "don't pad every claim to equal weight".
4. **Low burstiness.** Uniform sentence length/structure: GPTZero's founding
   feature, corroborated independently (Muñoz-Ortiz, 2308.09067; Reinhart,
   PNAS 2410.16107). Human sentence-length CV is simply higher. → the
   scorer's burstiness metric and the ≥0.45 gate.
5. **Register rigidity.** LLMs hold one polished expository voice regardless
   of situation; humans shift register (Reinhart). → L4.
6. **Stance asymmetry.** Humans: first-person stance, modals, selective
   epistemic hedging, discourse-marker cohesion. LLMs: nominalizations,
   formal connectives, paragraph-architecture cohesion (Herbold, 2304.14276).
   → L4's hedging rules and "connective texture over scaffolding".
7. **Syntax signature.** Nominalization density, present-participial
   clauses, longer constituents (Reinhart; Muñoz-Ortiz). → de-nominalize;
   kill participial openers.
8. **Affect skew.** LLM text is joy-skewed and uniformly positive
   (Muñoz-Ortiz). → widen affect.

## Why the scorer measures features, not detector verdicts

Detectors are brittle: RAID (2405.07940) shows trivial perturbations fool
them, and DIPPER (2303.13408) shows one paraphrase pass drops DetectGPT from
70% to 4.6% detection. Verdicts are therefore neither necessary nor
sufficient. The features they key on, however, are exactly what human readers
report as "sounds like AI" — so the scorer tracks the features directly:
weighted tell density, lexicon hits, burstiness, formatting densities,
register signals. Passing the gate means "the measurable tells are gone",
which is the honest, robust target.

## What rewriting cannot do (the honesty boundary)

- Retrieval/watermarking by providers survives any rewrite (DIPPER's
  conclusion). Fine — this skill's goal is reader-experienced quality, not
  evasion.
- Character-level tricks and fake typos fool detectors (RAID) but degrade
  writing. Banned.
- Hollow content scores clean on every surface metric. Only the removal test
  catches it, which is why the judgment pass can never be skipped and why
  hollow spans are flagged, not padded.

## Practitioner corroboration

Paul Graham's "Write Like You Talk" and "How to Write Usefully" predate LLMs
and independently prescribe the same counters: spoken register (high
perplexity relative to formal boilerplate), maximal-strength claims without
overclaiming, qualification as precision. Wikipedia's WP:AICATCH — the
largest human-curated corpus of caught-in-the-wild AI text — converges on the
same tell families and adds the cluster rule this skill inherits: one tell is
coincidence; many tells, repeatedly, convict.

## Negative results: trained classifiers

Several trained-classifier approaches were evaluated for an additional
detection channel. None shipped, and the reasoning generalises beyond the
specific methods.

**The ones that added nothing.** Two well-established classifier families were
ruled out on published evidence: one shows no measurable gain over a simpler
model on text classification while adding a dependency to a package whose value
includes having none, and the other models a sequence signal that the burstiness
and followability statistics already capture more cheaply and more legibly.

**The one that worked, and was cut anyway.** A trained channel built on lexical
frequency and stylometric features performed well in-domain: 0.985 AUC and 94%
accuracy on held-out data, properly calibrated with an abstain band. It was
built, integrated, and then removed. The transfer test is why. Trained on
2022-era text, it rated 2026-era AI drafts as human at a mean probability of
0.038, and in a live check returned 0.33 on a passage the pattern meter scored
100 out of 100. Detector decay across model generations is well documented
(RAID, arXiv:2405.07940); this was that decay measured directly. A channel that
is confidently wrong on current text is worse than no channel, even reported
separately and labelled a second opinion.

The lesson generalises. Interpretable surface features degrade gracefully as
models change, because updating them means editing a data file and the drift is
visible in the diff. A trained classifier degrades silently, and silence is the
failure mode you cannot audit.

## Fairness: who a false positive lands on

Liang et al. ran seven commercial GPT detectors over two human-written corpora,
US eighth-grade essays and TOEFL essays by non-native English speakers. Native
samples scored near-perfectly. **More than half of the non-native samples were
misclassified as AI-generated** (arXiv:2304.02819; *Patterns* 4:100779, 2023).

The mechanism matters more than the headline. The same study found that
enriching word choice in the non-native samples reduced misclassification,
while simplifying the native samples increased it. The detectors were keying on
linguistic complexity, so anything measuring "does this read as polished" will
penalize the writers with the least room to perform polish.

That is a direct hazard for this skill, which measures surface features by
design. Two consequences are load-bearing rather than decorative. Burstiness
and followability are scored as *bands*, not as "more is better", so plain
sentences are never evidence on their own. And
`data/corpus/must-not-flag/esl-engineer-email.txt` is in the corpus every new
pattern must clear, so the reflect loop cannot learn a rule that convicts
competent non-native writing however many people cut the phrase.

## The reflect loop: why recurrence is the gate

The learning path (`scripts/learn.py`) takes its labels from the difference
between what the skill returned and what the author published. Two design
choices come from the failure modes above rather than from preference.

*Learning must be two-directional.* A loop that only adds patterns can only
grow, and a detector that only grows converges on flagging everything —
which, per Liang, lands hardest on the writers already over-flagged. So a
pattern the author overrules repeatedly loses weight.

*A single edit is not evidence.* Authors cut for length, fix facts, and change
their minds, and none of that is a style signal. Requiring the same span across
three independent documents is a crude significance test: it separates a
construction that recurs across unrelated writing from one person's sentence.
The same property is what makes an upstream contribution shareable without
carrying private text.

The honest limit: this measures what *writers who use the skill* strike, not
what readers detect. It tracks the register those authors are editing away
from, which is the target, but it is a convenience sample and no substitute for
the frequency work in `calibrate.py` against a real corpus.
