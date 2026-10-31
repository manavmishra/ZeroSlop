---
name: zero-slop
license: MIT
metadata:
  version: "2.12.33"
  author: manavmishra
description: Edit drafts into natural prose, inspect AI-sounding patterns, or review how a specified audience might respond passage by passage. Zero Slop runs inside the user's existing AI assistant with local tools that protect source details. Use for humanizing or de-slopping writing, polishing outward-facing prose, social drafts, final editorial checks, or an explicit simulated reader review. Preserve facts, voice and format; reader simulations are hypotheses, not human feedback.
---

# Zero Slop

A linter for the AI accent. The things that make prose read as machine-written
are measurable, so measure them, fix them, and show the numbers.

Zero Slop is a skill, not an AI model. The user's existing AI assistant, powered
by Claude, GPT, or another compatible model, reads the draft, understands its
context, and performs the editorial work. The bundled local tools handle
repeatable checks. They do not replace the assistant, and no separate Zero Slop
model or service receives the draft.

The separately invoked npm `zero-slop deslop` command and hosted MCP/REST endpoints
send a draft to Zero Slop's remote service. They are opt-in alternatives, not local
checks in this workflow. Do not invoke them as part of an offline skill run without
the user's request. The npm `score` command continues to run locally.

The science in one paragraph: detectors (and readers) key on the *post-training
register* — text that sits at the most-probable phrasing, with uniform sentence
rhythm, a few hundred over-represented style words, tidy template structure, and
relentless even polish. These signals live in the surface realization of the
text and can usually be revised without changing the meaning; the fidelity and
semantic checks below enforce that boundary. `references/evidence.md` has the
citations, and the ladder below orders the signals by measured strength.

## Hard rules (non-negotiable)

For an explicit character-cleanup request, use the bundled offline text-hygiene
helper at `scripts/text_hygiene.py` when available. It inspects formatting
characters and removes only a
small reviewed set of embedded artifacts in 16 common ASCII prose words.
Only sentence-shaped lines with conservative prose openers are eligible.
Recognized code, command syntax, URLs, formulas, quotations and multilingual
formatting are excluded; these guards are not a complete code parser. Preserve
uncertain text and use inspection when its purpose is unclear.
This is a separate local operation, not a replacement for contextual editing.
Its change record can reverse the exact cleanup. A scriptless assistant must
not claim byte-level cleanup it did not perform. Character cleanup does not
verify removal of statistical watermarks from ChatGPT, Claude, Gemini or any
other model. Preserve required disclosures and attribution.
In a host that routes local checks through the bundled MCP connector, use its
`clean_text` tool with the supplied text and optional `inspect: true` instead.

1. **Fidelity.** Meaning, claims, and facts survive exactly. Never invent a
   number, name, anecdote, or experience — and experiential/interior claims
   count ("by test day it felt familiar", "I was terrified"): if the author
   didn't say it, it's fabrication, even when it would make the piece land
   better. Preserve the underlying emotion or position when the author states
   one. A generic promotional intensifier may be reduced only when it is a
   named delivery defect and the underlying claim remains ("incredibly
   excited" may become "excited"). A hedge, scope limit, caveat, factual degree,
   or change of speaker is not promotional padding and must keep its strength.
   Specificity without source grounding is fabrication — worse than the slop it
   replaces.
2. **Flag hollow spans, don't fill them.** Prose that makes no claim cannot be
   rescued by rewording. Flag it and ask for the missing substance.
3. **No over-correction.** Trading AI-slop for edgy-slop (forced hot takes,
   fake first person, performed candor, staccato drama) is failure. Read
   `references/overcorrection.md` before heavy rewrites.
4. **Idempotence in editing.** Text that already reads human returns unchanged. "Reads
   human" is a two-channel finding, never a score: a draft returns unchanged
   only after the scorer is clean *and* the step 2 performed-register pass has
   run on it and reported zero findings. The best edit is often small. A reader-only
   review leaves every draft unchanged without certifying that it is clean. In
   scriptless mode, leave a draft unchanged when direct review finds no grounded
   edit, but do not certify it as scored or fully clear.
5. **Honest use.** This skill improves writing quality and voice. Refuse
   requests to defeat AI-disclosure requirements (schools, journals, employers
   that require disclosure) or to impersonate a named individual.
6. **Speak to the writer, not the scoring code.** User-facing reports must use
   ordinary editorial language. Say "writing score," "flagged phrases,"
   "sentence variety," "readability," "facts preserved," and "final checks."
   Never expose internal labels such as "surface score," "weighted tells,"
   "tell density," "burstiness," "followability," "fidelity gate,"
   "scorecard," "heatmap," "artifact," "candidate," or "overlay." Keep
   internal field names only in machine-readable JSON or maintainer notes.
7. **Tell the writer who did what.** Zero Slop is the skill and set of local
   tools; the AI assistant running it performs the contextual reading and
   editing. In every standalone report, name the current assistant or model
   only when the environment makes that identity certain. Say "Claude," "GPT,"
   or the accurate product name when known; otherwise say "your AI assistant."
   Never guess. Do not imply that a separate Zero Slop model or service
   received, read, or rewrote the draft.
8. **A clean score is not a completed review.** The scorer sees only the
   lexically anchored subset of the tells. Every rewrite or slop-inspection draft gets the
   performed-register pass in step 2 regardless of what the meter says, and
   that pass reports its counts — including zero — in the step 9 summary. A
   score in the "clear" band is a reason to look harder at register, not
   permission to stop: the tell families the meter cannot see are exactly the
   ones still standing when it comes back empty. A standalone audience reader
   review is a different diagnostic: it neither runs nor certifies this pass.

## Eight roles, one pipeline

Run the rewrite workflow as eight ordered responsibilities. They are editorial jobs,
not eight models or services. In an installed assistant, use role-isolated passes when
the harness can do that without extra network calls. When a service has a one-request
budget, combine the AI responsibilities into one structured editorial response and
run the local checks before and after it. Name that consolidation honestly; one model
response is not independent review.

Preserve source material rather than sentence count. Delete before rewriting: keep
a sentence when it adds a fact, position, reason, example, instruction, or necessary
connection. Delete empty sentences instead of replacing their flagged words with
milder synonyms. Do not add a takeaway or benefit summary that repeats a nearby
point. For example, delete “Efficiency is paramount” instead of changing it to
“Efficiency is crucial.” After a measured improvement in setup time, do not append
that the change “makes it easier to get started.” Preserve substantive opinions,
emotion, and useful transitions even when they contain flagged wording. Leave clear
factual statements and qualifications unchanged where possible. Missing knowledge
stays missing: “not measured beyond the first month” does not establish that the
first month was measured, and a missing feature in a new product does not establish
that the old product had it.

Delete attention-directing frames when the fact carries its own weight: “The number
I keep coming back to is 119,000” becomes the sentence that states what 119,000
measures. Then apply the removal test to the next sentence too. If “The price cut paid
for the extra thinking” only restates that lower token prices offset higher token use,
delete it rather than preserving the recap as voice or rewriting its metaphor.

Keep local and AI responsibilities distinct:

1. **Scorer — local tools.** Point to exact phrases and problems with rhythm,
   readability, formatting, and register; explain the writing score.
2. **Interpreter — the AI assistant.** Read the full draft for claims, support,
   audience, genre, structure, and voice before changing it.
3. **Rewriter — the AI assistant.** Remove stock wording, then rebuild order, rhythm,
   and tone while preserving the author's material.
4. **Fact gate — local tools.** Reject rewrites that add or drop names, numbers,
   quotations, or links; among the rest, select the version that best clears the
   measured checks. This local check cannot certify reframed claims or invented
   interior meaning; the verifier handles those with contextual comparison.
5. **Copy desk — the AI assistant.** Correct grammar, spelling, punctuation, usage,
   diction, and consistency in the selected text.
6. **Read-aloud editor — the AI assistant.** Read the complete copy-edited text aloud
   and directly fix stumbles, repetition, weak transitions, and awkward flow.
7. **Verifier — local tools plus the AI assistant.** Check the exact final text
   against the source for the writing score, facts, meaning, qualifiers, voice,
   format, and structure. A warning prevents an unqualified approval; it never erases
   a source-safe edit or starts an open-ended loop. Apply at most one targeted repair,
   then rerun the local checks on the exact changed text.
8. **Fresh-eyes finalizer — the AI assistant.** Read the verified text as a first-time
   reader and apply only safe final polish. If it changes the text, rerun the local
   score and fact checks once. Deliver the safest edit with a plain warning if a
   remaining concern would require another model request or a guess.

This is an engineering separation of responsibilities, not a claim that research has
proved eight to be the uniquely correct number. Studies support several different
signal families and several different editorial failure classes; no single score or
prompt can cover them all. The local roles provide repeatable measurements. The AI
roles supply contextual judgment and editing. A generating role does not certify its
own factual safety. Role 7 supplies the local release checks; role 8 confirms that the
result reads cleanly to someone seeing it for the first time. In a one-request service,
the model's self-check is editorial guidance, not independent verification.

## Detailed workflow

Before starting the eight-role pipeline, read and follow the complete detailed workflow in references/detailed-workflow.md. Keep every rule in this entry and the existing references.

[Detailed workflow](references/detailed-workflow.md)

## References

- `references/reader-review.md` — opt-in audience-response review, sequential
  context boundaries, skim preview, notes-only follow-ups and revision comparison.
  `scripts/reader_review.py` prepares passage packets and a local review page;
  it does not simulate readers or call a model itself.
- `references/tells.md` — the master taxonomy (115 tells, 6 families) with fixes.
  It is the human-readable catalogue; `data/patterns.json` is its machine
  implementation. Together with the reviewed shared overlay, the current
  release carries 294 weighted regexes because some tells need more than one.
- `references/rewrite-moves.md` — the positive program: the six ladder rungs
  expanded, with before/after pairs and voice calibration.
- `references/platforms.md` — LinkedIn, X/Twitter, email, blog, newsletter,
  research modules. Read the matching one whenever genre is known.
- `references/overcorrection.md` — edgy-slop catalogue, what NOT to flag, and
  the signs of human writing to preserve.
- `references/readalong.md` — the mandatory, separate read-aloud pass that
  fixes flow, cohesion, and stumbles directly in the deliverable.
- `references/fresh-eyes.md` — the first-time-reader finalizer and its bounded
  one-recheck rule.
- `references/copy-desk.md` — the grammar, spelling, and style pass that prepares
  the selected rewrite for read-aloud finalization.
- `references/eval.md` — the pass/fail checklist for roles 7 and 8. It carries the
  contextual and register families the meter cannot express as patterns, and it
  requires the section A counts to be written down rather than judged silently.
- `references/evidence.md` — the research basis: papers, detector mechanics,
  and why each ladder rung is ordered where it is.
- `scripts/rescue.py` — the conservative, no-network availability editor shared by
  installed skills and the web demo. It returns a changed draft when a known safe edit
  is available, then leaves approval to the scorer and fact gate.

## Worked example (LinkedIn)

**Before (writing score 100):**
> 🚀 I'm beyond excited to announce that after 18 months of hard work, we've
> raised $4.2M to transform how teams ship software! This wasn't just a
> milestone — it's a testament to our incredible team. Here are 3 lessons I
> learned along the way… Agree? 👇

**After (writing score 9.5):**
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
(step 9 flags), never manufacture it.
