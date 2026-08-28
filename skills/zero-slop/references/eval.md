# Zero Slop eval

Answer every check with pass or fail. Where a check asks for a count, write the
number down; a count is evidence, and a missing count means the pass did not run.

Any fail sends the text back through the copy desk and read-aloud pass, after which
every check here runs again on the new text. Limit that loop to three rounds.

**This file exists because the meter cannot see most of what is on it.** The scorer
reads the lexically anchored subset: listed phrases, sentence-length variance,
readability, formatting density. Everything in section A is a property of the whole
document rather than of any span, so no pattern can reach it. A clear score is a
reason to work through section A carefully, never permission to skip it.

The ratchet: every miss an audit, a competitor, or a reader catches becomes a
deterministic detector or a `data/corpus/must-flag/` fixture in the same change.
A note is not a fix; `register.py --recall` proves each recorded miss still
gets caught, and the release suite runs it.

Families here are drawn from the Zero Slop tell catalogue, from Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
maintained by WikiProject AI Cleanup, and from the checks in petergyang/no-ai-slop
and blader/humanizer. Every check that needs one carries a worked before and after,
because an abstract instruction gets a partial answer.

Roles 7 and 8 own this file. Role 8 answers section F. A role that generated text
never grades that text.

Scoring this file is meaningless: it quotes tells as examples, so the meter flags its
own catalogue. That is the documented exception for material quoted as an example, and
it is a good candidate for `data/corpus/must-not-flag/`.

## A. Register, which the meter cannot reach

Run every item on every draft, including one that scored clear. Record the counts in
the report even when they are zero.

1. **Antithesis pairs. Count: ___** Two balanced statements where the second lands a
   twist. Count all four shapes, and note that most carry no negation marker at all:
   marked ("Not perfect. Honest."), bare subject swap ("Llama is open-weights. Dolma
   releases the data."), isocolon with the arguments swapped, and unmarked reversal.
   Budget is one per piece. Two is a finding. Three or more under 500 words means the
   register failed whatever the score said.
2. **Binary contrast, the subtractive form. Count per 1,000 words: ___** The
   corrective appositive: "X, not Y." "A rather than B." Each instance is usually
   good, careful writing, which is why the meter has no rule for it. The defect is
   density. Above roughly 4 per 1,000 words, the document has one rhetorical move
   instead of a voice.
3. **Significance scaffolding. Count: ___** A sentence announcing that a point
   matters instead of delivering it. Budget is zero.
4. **Negative definition.** Does the draft repeatedly say what a thing is not before
   saying what it is? One is a useful disambiguation, a habit is a tic. Stacked
   negation counts: "No file monitoring, no browser hooks, no reaching into where you
   publish" becomes "Zero Slop reads only what you hand it."
5. **Comma-series density. Count per 1,000 words: ___** Enumerations of three or more
   noun phrases. Technical writing legitimately enumerates, so this is a reading
   judgment rather than a threshold: are the lists carrying information, or has the
   sentence shape become the default? Convert the longest to real lists.
6. **Robotic symmetry.** Repeated sentence shapes, identical paragraph geometry, stacked
   punchy fragments, uniform paragraph length. Check table columns too: seven of eight
   cells opening with a verb and a comma list of abstract nouns is the same defect
   inside a grid.
7. **Colon reveals.** A noun phrase, a colon, then a lowercase dramatic payoff.
   Colons are for lists, labels, and quotations.
8. **Throat-clearing openers.** "Here's the thing." "Let me be clear." "To be
   honest." Cut and state the point.
9. **Faux-insight setups.** "What most people get wrong." "The part everyone misses."
   These flatter the writer as sole expert. Make the claim stand alone.
10. **Rhetorical setups.** "What if I told you." "Think about it:" Self-answered
    question and answer pairs.
11. **Fake-profound kickers.** Delete the closing aphorism rather than rewriting it
    into a better metaphor. End on the clearest concrete sentence already present.
12. **Summary-recap endings.** The reader was just there.
13. **Theatrical framing and extended conceit. Count: ___** An ordinary process
    dressed as a courtroom, a heist, or a diagnosis. Budget is one metaphor.
14. **Superficial analysis.** Trailing participial clauses that pretend to explain
    significance: highlighting, underscoring, reflecting, showcasing.
15. **Importance puffery.** "Marks a pivotal moment." "Stands as a testament." State
    the fact and let the reader weigh it.
16. **Interpretive metadiscourse.** Lines that step outside the subject to tell the
    reader what to notice or how much weight to give it.
17. **Weasel attribution.** "Studies show." "Experts agree." Name the source, or flag
    it for the writer. Never invent one.
18. **Adjective inflation and hollow intensifiers.** "a real improvement", "actual
   results", "a genuine breakthrough", "true value". Delete the adjective; the noun
   carries the claim or it does not. Distinct from empty adverbs (next): adverbs pad
   the verb, these inflate a noun, and a span that is neither belongs to importance
   puffery. Measured by the meter; the reading pass owns only the shapes the noun
   list misses.
19. **Empty adverbs and filler frames.** Adverbs: "just", "simply", "actually",
    "literally", "honestly", "fundamentally", "inherently", "inevitably". Frames:
    "the reality is", "the truth is", "in terms of", "with regard to", "going
    forward", "in this article". Cut each one that adds nothing; keep the ones
    carrying real emphasis, uncertainty, contrast, or the writer's spoken rhythm.
    Distinct from adjective inflation (previous): these modify verbs and clauses.
    The meter does not flag these globally because they are ordinary in honest
    writing, so this is a judgment per instance. "just", "simply", "actually", "literally",
    "honestly", "fundamentally", "inherently", "inevitably". Cut each one that adds
    nothing; keep the ones carrying real emphasis, uncertainty, contrast, or the
    writer's spoken rhythm. This is a judgment per instance, which is why the meter
    does not flag these words globally: they are ordinary in honest writing.
20. **Nominalization and weak verb phrases.** "Made a decision" for "decided",
    "needs removal from" for "you cut from". De-nominalize, and prefer a direct verb
    with an actor.
21. **Fake-strong verbs.** Prefer "is" and "has" where they are clearer.
    "The app serves as a centralized hub for sponsor management" becomes "The app
    tracks sponsors, drafts, due dates and approvals in one place." Monument verbs
    count too: "stands on", "sits atop", "marks a".
22. **Reasoning-chain artifacts.** Working-out left in the answer: "Let me think
   through this", "First I'll consider", a restated plan before the plan. The reader
   wants the conclusion, not the deliberation.
23. **Emotional flatline.** Uniform affect across a piece that should vary. Nothing
   irritates the writer, nothing surprises them, nothing costs anything. Real writing
   has range.
24. **False concession.** "While X has merit, Y" where X was never a live position
   and nothing follows from conceding it. Keep a real counterargument; cut a straw one.
25. **Confidence-calibration phrases.** "I'm fairly confident", "with high certainty",
   "to be clear, this is my read". Calibrated hedges are fine when they carry real
   uncertainty; these announce a posture instead.
26. **Parenthetical hedging.** Qualifiers tucked in brackets so the sentence can claim
   more than it supports: "The fix works (in most cases) for every driver."
27. **Engagement hooks and endorsement closers.** "You won't believe", "Sound
   familiar?", "Give it a try and let me know", "Trusted by teams everywhere".
   Infomercial register, wherever it appears.
28. **Lingering-attention claims.** "This will stay with you", "you'll be thinking
   about this for weeks". The writer cannot know the reader's future.
29. **Generic positive endings.** A closing paragraph that resolves into optimism
   without a concrete next step: "The future looks bright for teams willing to adapt."
30. **Synonym cycling.** If the clear word is right, repeat it. Do not rotate terms
    for style. "The agent reviews the draft. The assistant scores the piece. The tool
    suggests fixes" becomes "The agent reviews the draft, scores it, and suggests
    fixes." Check every referent, not the first one you notice: a role table is where
    a second and third name usually appear.

## B. Substance

31. **Removal test.** Does every paragraph lose something real when deleted?
32. **Relevance test.** Does every paragraph serve the brief, audience, and argument?
33. **Front-loading, applied selectively.** Conclusions arrive early where that helps
    the reader, without forcing every section into the same point-then-detail shape.
34. **Paragraph-order dependence.** Could several prose paragraphs be shuffled without
    harming the argument? Reference material, FAQs, and independent findings are
    exempt.
35. **Unsupported novelty.** "Nobody is naming this" needs an actual comparison.
36. **Self-labeling significance.** "This matters" needs a consequence.
37. **Moral-adjective category error.** Calling a technical choice brave or honest
    needs a moral agent.
38. **Portability test.** Could any sentence move unchanged to another company,
    product, or person? Cut it or make it specific.
39. **Statistics cohesion.** Does each test or dataset get its own paragraph opening
    with what it checks in plain words, before the numbers?
40. **Cross-references resolve.** Every named artefact, panel, dataset, or prior
    result is defined on first use or linked to where it lives. "The prior 84.2%
    result on the 38-item editorial panel" tells a reader nothing if neither the
    panel nor the packet is named anywhere.
41. **Internal pointers name their target.** "In the references", "see the docs",
    "as documented elsewhere" point at nothing. Name the file and the section, and
    link it, the way an external citation would be named.
42. **Numeric precision matches the measurement.** Five significant figures on a
    single run of a single machine claims a stability the method cannot support.
    Round to what the measurement earns, or state the spread.
43. **Hollow spans flagged, not filled.** Prose that makes no claim was flagged for
    the writer rather than reworded into something that sounds like one.
44. **Sycophantic tone.** Generic validation of the reader that carries no content:
    "Great question", "Excellent point", "You're absolutely right". It echoes nothing
    back, it only rewards. Cut it and start with the answer.
45. **Recap-flattery.** An opener that echoes the reader's *own work* back at them
    dressed as gratitude, ahead of the point: "Thanks for all the legwork here, the
    migration script and the rollback plan you worked through are what made this
    possible." They already know what they did. A real thank-you is one clause and
    moves on: "Thanks for the legwork, this looks right, one comment below."
46. **Acknowledgment loops.** Restating the question or the prior section before
    answering it. This echoes the *context*, where recap-flattery echoes their *work*
    and sycophancy echoes *nothing*. Ask what is being echoed; that is what separates
    these three.
47. **Wall-of-text reply.** Paragraphing that hides a sequence the reader needs. A
    long narrative paragraph is not a wall of text merely because it is long; the tell
    is a buried list of steps or options.

## C. Fidelity

48. **Scripted check run, not eyeballed.** `slopscore.py --fidelity` exits zero.
49. **No invented specifics.** No number, name, anecdote, date, or source appeared
    that the author did not supply.
50. **No invented interior claims.** No stated feeling, motive, or experience the
    author never wrote.
51. **Qualifiers survive.** Hedges, scope limits, and caveats carry the same strength
    as the source.
52. **Claims not reframed.** Same names and numbers can still carry a changed
    emphasis or implication. Compare meaning, not tokens, and run three direction
    tests on every span `register.py --delta` reports as inserted or rewritten:
    purpose has not become outcome ("changed tactics to achieve its objective" is
    not "changed tactics until it reached its objective"); agency has not moved
    ("helps teams generate fixes" is not "generates fixes"); a warned future has
    not become an asserted present. These are contextual comparisons against this
    source, never a word list.
53. **Non-prose untouched.** Code, front matter, tables, blockquotes, identifiers,
    paths, and heading hierarchy intact.

## D. Voice and readability

54. **Expert voice.** A respected practitioner sounds at home: precise terms used
    correctly, authority earned through specifics, no hedging into mush.
55. **Followability.** A smart first-time reader follows each sentence on the first
    pass. One idea per sentence; every abstraction anchored in the same breath; never
    three or more abstract noun phrases stacked.
56. **Voice preserved.** Would the writer recognize this as theirs? Distinctive
    vocabulary, cadence, bluntness, humor, uncertainty, and digressions survived.
57. **Strong sentences left alone.** Nothing was rewritten merely for consistency.
58. **Active voice with human subjects.** People do the verbs. Passive stays only
    where the actor is unknown, irrelevant, deliberately withheld, or native to the
    genre.
59. **Proportional cutting.** No compression that stripped character. Density is
    information per word, not fewer words.
60. **Read aloud.** Would this sound natural read to a sharp colleague?
61. **Emphasis survives.** `register.py --delta` lists every intensifier or
    absolute the rewrite cut from this source. Each cut needs a defect named from
    this file, judged in its own context: puffery, hyperbole universal, filler.
    "Too strong" is not a defect, and a falsifiable claim the author owns keeps
    its full strength whatever word carries it. Cutting "changed overnight" from
    a claim the author would defend cost a blind head-to-head once.
62. **Earned length.** `--delta` lists every run of three or more words the rewrite
    added. Each must restate meaning already in this source for this audience; a
    bridge or an unpacked definition can qualify, scaffolding the author never
    wrote cannot. A rewrite longer than its original defends every insertion or
    loses them.
63. **No over-correction.** AI slop was not traded for edgy slop: forced hot takes,
    fake first person, performed candor, staccato drama.

## E. Form

64. **Returned in the format it arrived in.** A .docx comes back a .docx.
65. **Reader language.** No evaluator or harness vocabulary leaked into the copy:
    candidate, artifact, overlay, gate, scorecard, burstiness.
66. **Formatting slop.** No emoji headings, decorative bold, or bullets that should be
    prose. Count the headings over one or two sentences: four consecutive H3s each
    wrapping a code block and one line is a section that wants to be one section.
67. **Em dashes.** None in short copy. One or two in a long draft only where they
    clearly beat a comma, period, or parenthesis.
68. **Hyphenated modifier stacking.** "AI-powered cloud-native data-driven platform".
   Two stacked compound modifiers in one noun phrase is a tell; keep the hyphens
   grammar requires and cut the rest.
69. **List-label periods and bare-noun bullets.** Bullets that are fragments ending in
   full stops, or a list of bare noun phrases with no predicate. Either make them
   sentences or make them a real list.
70. **Numbered-list inflation.** A numbered list where order carries no meaning, or a
   list padded to a round number. Use a bulleted list, or prose.
71. **Chatbot artifacts.** Citation markup leaks, "Regenerate response", tool URL
   parameters such as utm_source, and any assistant scaffolding left in the copy.
72. **Attribution accurate.** The report names who did what without guessing which
    model is running, and never implies a Zero Slop service read the draft.

## F. Process integrity

Role 8 answers this section. It is the check no single-agent eval can make.

73. **Roles stayed separate.** The copy desk, read-aloud pass, verification, and
    fresh-eyes review each ran as a distinct pass.
74. **No self-certification.** No role graded text it generated.
75. **Counts reported.** Every count in section A appears in the summary, including
    the zeros.
76. **The exact final text cleared every check.** Not an earlier draft, not a version
    that was repaired afterward.
77. **Role 8 approved without changes.** If it changed anything, roles 5 through 8
    ran again on the revision.
78. **Fallbacks named honestly.** If the three-round limit was reached, the report
    says which check failed and does not describe the result as fully verified.
