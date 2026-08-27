# The final copy desk

Run this pass on every deliverable after the rewrite and initial verification
work. It corrects mechanics and line-level style before the final read-aloud
pass. Its job is to produce corrected copy, not an assessment of copy that still
needs work.

Use a dedicated copy-editor agent with fresh eyes when the harness supports
subagents. Otherwise, set aside the writing mindset and perform the same review
as a separate, role-isolated pass. Either way, apply every accepted correction
to the actual deliverable before sending it to the final read-aloud pass.

## What to correct

Read the complete piece from title to final line, including headings, captions,
list items, table labels, calls to action, and user-authored alt text. Correct:

- spelling, typos, duplicated or missing words, and inconsistent regional usage;
- grammar, agreement, tense, articles, prepositions, pronouns, and modifiers;
- punctuation, capitalization, quotation marks, hyphenation, and compound terms;
- broken parallelism, unclear antecedents, misplaced clauses, and ambiguity;
- awkward syntax, needless repetition, imprecise diction, and choppy transitions;
- phrasing that is stiff, clumsy, fussy, unintentionally casual, or unprofessional;
- internal scoring, editing, or workflow labels that have leaked into reader-facing
  prose; replace each with plain language unless the audience needs the technical
  term;
- inconsistencies in terminology, headings, labels, voice, and editorial style.

Aim for tasteful, elegant, professional prose in the register the piece calls
for. Elegance means precise, natural, and restrained. It does not mean ornate,
formal, promotional, or generic. Preserve warmth, humor, contractions, fragments,
dialect, and technical language when they are intentional and suit the genre.
Keep the author's regional spelling unless the user or publication specifies a
different house style.

## Boundaries

- Preserve every fact, claim, qualifier, number, name, date, link, and source.
- Do not invent detail, strengthen certainty, soften a warranted conclusion, or
  change the author's position for smoother prose.
- Do not edit quotations, code, commands, identifiers, file paths, data, legal
  boilerplate, or proper names unless the user explicitly asks.
- Preserve the input format and all non-prose structure. Correct content inside
  a structured form without changing the form itself.
- Do not replace a distinctive human phrase merely because a more conventional
  phrase exists. Correct errors and genuine awkwardness, not personality.
- When a sentence is ambiguous and the intended meaning cannot be recovered
  safely, leave it unchanged and flag the ambiguity instead of guessing.

## Copy-editor agent brief

Give the agent the genre, intended audience, original draft, selected rewrite,
known voice signals, and immutable facts when available. Then use this brief:

> You are the copy editor for a publication-ready piece. Edit the complete
> text directly and return the corrected version in the same format. Fix every
> genuine error in spelling, grammar, punctuation, capitalization, agreement,
> tense, modifiers, syntax, diction, consistency, and usage. Improve awkward,
> unclear, repetitive, clumsy, or unprofessional phrasing where the meaning is
> certain. Remove internal evaluation or workflow language from outward-facing
> prose when plain language says the same thing. Make the prose tasteful, elegant,
> precise, natural, and appropriate for its genre and audience. Preserve the
> author's voice, regional spelling, facts, claims, qualifiers, names, numbers,
> links, structure, and intentional fragments. Do not add detail, hype, certainty,
> or generic polish. Do not alter
> quotations, code, commands, identifiers, or data. If a correction would
> require guessing what the author means, leave that span unchanged and flag it.
> Return: (1) the fully corrected text, not a list of suggestions; and (2) a
> terse note only for unresolved ambiguities or unusual forms deliberately kept.

Apply the corrected version to the deliverable, then send that exact artifact
through the read-aloud pass in `references/readalong.md`. Verify the
artifact returned by the read-aloud editor:

1. Rerun the heuristic surface scorer and scripted fidelity check.
2. Compare it directly with both the original and selected rewrite for preserved
   claims, qualifiers, intended voice, regional spelling, format, and non-prose
   structure. The script cannot detect every semantic or stylistic change.
3. If any check or comparison requires a repair, apply it, send the repaired
   text through the copy desk and read-aloud pass again, and repeat all
   final checks.

After verification, send that exact text through the finalizer in
`references/fresh-eyes.md`. Stop only when the same artifact clears the copy desk,
read-aloud pass, semantic and format review, scorer, fidelity check, and receives a
no-change fresh-eyes approval. Limit this repair loop to
three rounds. If an issue still cannot be resolved without guessing, return the best
source-preserving version that completed both editorial passes, flag the unresolved
span and failed check plainly, and do not describe the fallback as fully verified.
