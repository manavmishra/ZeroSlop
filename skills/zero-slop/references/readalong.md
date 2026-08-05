# The readalong pass

The scorer reads wording. Three of its four channels are wording-blind, and none
of them reads the document the way a person does — start to finish, one sentence
handing off to the next. That is where the failures a clean score cannot see
live: a sentence you trip over, a section that arrives cold, a caveat performed
three times in a row, one word drummed twice in a breath. A draft can pass every
threshold and still stumble when read aloud. This pass catches that.

Run it on every rewrite. On anything past ~400 words, run it as a **dedicated
pass with fresh eyes** — a subagent whose only job is to read aloud and flag
stumbles (brief below) — because the pass that just wrote the text has gone blind
to it.

## What to listen for

Read the whole rewrite aloud, top to bottom. Flag every spot that makes you
stumble, re-read, or wince. Quote the exact phrase and give a specific fix.

- **Stumbles.** Any sentence you trip over or must re-read: run-ons, garden
  paths ("if Python is missing the skill" reads as *missing the skill* until you
  back up), a heavy clause stack, an ungrammatical tail bolted onto a strong
  short clause.
- **Cold transitions.** A sentence or section that does not connect to the one
  before it — a topic that arrives with no hinge, a pivot the reader has to
  supply themselves.
- **Performed candor.** Announcing your own honesty ("honestly," "to be fair,"
  "the honest reading is") instead of just saying the thing. One earned caveat
  is disclosure; four in a row is throat-clearing, and throat-clearing is a
  machine tell.
- **Repetition.** A word or idea repeated too close together — across the whole
  document, not just within a paragraph. "Quick … quick" in one sentence;
  "rule" four times in six lines.
- **Register slips.** The expert voice dropping into folksy filler ("you just do
  without the number") or a proverb ("better to catch it than pretend it can't
  happen"), or overreaching into hype.
- **Number and antecedent snags you only hear aloud.** "A single em-dash … leans
  on them"; "One you keep overriding" before the reader knows what *one* is.
- **Clarity.** Anything a smart first-time reader would not follow on one pass.
- **Cohesion.** Places where two adjacent sections read as if different people
  wrote them, or where a name or claim is inconsistent across the document (a
  tool called "humanizer" in one paragraph and "blader" in the next).

Return a prioritized list, worst offenders first, then a per-section A–F grade on
read-aloud flow with the single highest-impact fix for each. Only flag what needs
work; say nothing about a sentence that already lands.

## The subagent brief

When the harness has subagents, hand the rewrite to one with this prompt. Fresh
eyes are the point — do not have the writing pass grade its own flow.

> You are a ruthless read-aloud editor. Below is [what it is] that must sound like
> one expert human wrote it — clear, confident, precise, naturally flowing when
> spoken, no marketing gloss, no AI slop, cohesive from section to section. Read
> it aloud in your head, top to bottom, and find every place it stumbles. For
> each problem, quote the exact phrase and give a specific fix. Hunt for:
> stumbles, cold transitions, AI/marketing tells, performed candor, register
> slips, repetition across the whole piece, clarity failures, and cohesion
> breaks. Then rate each section A–F on read-aloud flow with the single
> highest-impact fix for each. Only flag what needs work. Prioritized list, worst
> first.
>
> [paste the rewrite]

Apply the fixes, then re-run the scorer (the readalong can reintroduce a tell —
verify the number held) and confirm the fixes did not drop or invent a fact.

## Why it is separate from the gate

The numeric gate and the readalong catch different failures, so both run. The
gate rejects tells, uniform rhythm, and compression the reader can measure; the
readalong rejects the stumble, the cold pivot, and the performed caveat that no
threshold can. A rewrite passes only when both are clean.
