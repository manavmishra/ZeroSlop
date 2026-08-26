# The final read-aloud pass

The scorer measures wording and document-level patterns. The copy desk corrects
mechanics and line-level style. Neither evaluates the complete deliverable as a
listener hears it: from the first line to the last, with each sentence setting up the
next. A stumble, cold transition, unclear antecedent, or change of voice can still
survive a clean score and correct grammar.

Run this pass on every deliverable after the copy desk. It is the last editorial pass
before final verification and the Report step. Use a dedicated editor with fresh eyes
when the harness supports subagents; otherwise perform a separate, role-isolated pass.
The editor must fix the actual deliverable and return the corrected artifact in the
same format. An audit or list of suggestions is not a completed pass.

## What to fix

Read the complete copy-edited artifact aloud, from title to final line. Apply every
safe correction for:

- **Stumbles.** Repair run-ons, garden paths, heavy clause stacks, and awkward
  endings that make a reader stop or back up.
- **Cold transitions.** Add or repair the hinge when a sentence, paragraph, or
  section arrives without a clear connection to what came before.
- **Performed candor.** Remove announcements of honesty such as "honestly" or "to be
  fair" when the sentence can simply make its point.
- **Reflexive agreement.** Remove automatic praise or agreement that appears before
  the substance has been checked. Let the facts determine whether the draft agrees,
  qualifies, or disagrees.
- **Communicative drift.** Stop when fluent sentences no longer advance a clear
  point or reader need. Cut the passage, rebuild it around its purpose, or flag the
  missing intent rather than inventing one.
- **Rhetorical scale mismatch.** Reduce grand reveals, lessons, or contrasts when
  the underlying point is too small or unsupported for the framing. Preserve a
  contrast that corrects a real, supported misconception.
- **Performed-writer register.** Flatten theatrical framing of ordinary work ("we
  hired an adversary"), epigram closers, staccato antithesis pairs ("Not perfect.
  Honest."), extended conceits (billing, courtroom, forensics, recipe), one-word
  drama beats, hyperbole ("nothing on earth"), and cute meta-taglines into the
  plain statement each one replaced.
- **Stat pile-ups.** Split a paragraph that stacks several datasets or tests.
  Each test gets its own paragraph that opens with what it checks in plain words,
  numbers after the setup.
- **Repetition.** Fix a word, phrase, sentence shape, or idea repeated close enough
  to sound accidental.
- **Register slips.** Rewrite sudden marketing gloss, generic formality, or folksy
  filler to match the document's established voice.
- **Process-language leaks.** In outward-facing prose, replace internal labels such
  as "faithful candidate," "selected rewrite," or "exact artifact" with plain
  language. Keep those labels only when the document explains the machinery itself
  and needs the terms.
- **Number and antecedent snags.** Clarify singular/plural mismatches and pronouns or
  references whose meaning becomes uncertain when heard aloud.
- **Clarity.** Unpack anything a smart first-time reader would not follow in one
  pass.
- **Cohesion.** Resolve inconsistent names or claims, and repair transitions that
  make adjacent sections sound as if different people wrote them.

Do not merely flag these problems. Correct them directly wherever the intended
meaning is certain.

## Boundaries

- Preserve every fact, claim, qualifier, number, name, date, link, and source.
- Preserve the writer's intended voice, regional spelling, and genre-appropriate
  fragments.
- Do not alter quotations, code, commands, identifiers, file paths, data, legal
  boilerplate, or proper names unless the user explicitly asks.
- Preserve the input format and all non-prose structure, including tables, lists,
  diagrams, and markup.
- If a correction would require guessing, leave the span unchanged and flag the
  ambiguity. Flow never outranks fidelity.

## Read-aloud editor brief

Give the editor the genre, intended audience, original draft, selected rewrite,
copy-edited artifact, known voice signals, and immutable facts when available. Then
use this brief:

> You are the final read-aloud editor for a publication-ready piece. Read the
> complete copy-edited artifact aloud in your head, from title to final line.
> Edit it directly. Fix every genuine stumble, cold transition, unclear antecedent,
> accidental repetition, register slip, overloaded sentence, clarity failure, and
> break in cohesion. Remove internal scoring, editing, or workflow language that has
> leaked into outward-facing prose; prefer plain descriptions of what the text does.
> Preserve the writer's voice, regional spelling, facts, claims, qualifiers, names,
> numbers, links, quotations, code, commands, identifiers, data, and non-prose
> structure. Do not add detail, hype, certainty, or generic polish. If a correction
> would require guessing, leave that span unchanged and flag it.
> Return: (1) the complete corrected artifact in the same format, not an audit or
> list of suggestions; and (2) a terse note only for unresolved ambiguities or
> unusual forms deliberately kept.

Apply the returned artifact to the actual deliverable before verification.

## Finalization loop

Verify the exact artifact returned by the read-aloud editor:

1. Rerun the heuristic surface scorer and scripted fidelity check.
2. Compare it directly with the original and selected rewrite for claims,
   qualifiers, intended voice, regional spelling, format, and non-prose structure.
3. If any check requires a textual repair, apply it, run the copy desk again, run
   this read-aloud pass again, and repeat every final check.

Stop only when the same artifact has cleared the copy desk, final read-aloud pass,
semantic and format review, scorer, and fidelity check. Limit this repair loop to
three rounds. If an issue still cannot be resolved without guessing, return the best
source-preserving version that completed both editorial passes, state the unresolved
span and failed check plainly, and do not describe the fallback as fully verified.

## Why it is separate

The numeric gate, copy desk, and read-aloud pass catch different failures. The gate
measures tells, rhythm, formatting, and compression. The copy desk corrects mechanics
and line-level usage. The read-aloud editor fixes the stumble, cold pivot, repetition,
and broken handoff that neither threshold nor grammar rule can hear. A deliverable is
finished only after the exact text returned to the user has cleared all three stages
and every final verification check.
