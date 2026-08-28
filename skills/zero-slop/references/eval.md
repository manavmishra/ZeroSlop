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
   saying what it is? One is a useful disambiguation. A habit is a tic.
5. **Comma-series density. Count per 1,000 words: ___** Enumerations of three or more
   noun phrases. Technical writing legitimately enumerates, so this is a reading
   judgment rather than a threshold: are the lists carrying information, or has the
   sentence shape become the default? Convert the longest to real lists.
6. **Robotic symmetry.** Repeated sentence shapes, identical paragraph geometry,
   stacked punchy fragments, uniform paragraph length down the page.
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
18. **Empty adverbs and filler frames.** Adverbs: "just", "simply", "actually",
    "literally", "honestly", "fundamentally", "inherently", "inevitably". Frames:
    "the reality is", "the truth is", "in terms of", "with regard to", "going
    forward", "in this article". Cut each one that adds nothing; keep the ones
    carrying real emphasis, uncertainty, contrast, or the writer's spoken rhythm.
    The meter does not flag these globally because they are ordinary in honest
    writing, so this is a judgment per instance. "just", "simply", "actually", "literally",
    "honestly", "fundamentally", "inherently", "inevitably". Cut each one that adds
    nothing; keep the ones carrying real emphasis, uncertainty, contrast, or the
    writer's spoken rhythm. This is a judgment per instance, which is why the meter
    does not flag these words globally: they are ordinary in honest writing.
19. **Nominalization and weak verb phrases.** "Made a decision" for "decided",
    "needs removal from" for "you cut from". De-nominalize, and prefer a direct verb
    with an actor.
20. **Fake-strong verbs and synonym cycling.** Prefer "is" and "has" where they are
    clearer. If the right word is right twice, use it twice.

## B. Substance

21. **Removal test.** Does every paragraph lose something real when deleted?
22. **Relevance test.** Does every paragraph serve the brief, audience, and argument?
23. **Front-loading, applied selectively.** Conclusions arrive early where that helps
    the reader, without forcing every section into the same point-then-detail shape.
24. **Paragraph-order dependence.** Could several prose paragraphs be shuffled without
    harming the argument? Reference material, FAQs, and independent findings are
    exempt.
25. **Unsupported novelty.** "Nobody is naming this" needs an actual comparison.
26. **Self-labeling significance.** "This matters" needs a consequence.
27. **Moral-adjective category error.** Calling a technical choice brave or honest
    needs a moral agent.
28. **Portability test.** Could any sentence move unchanged to another company,
    product, or person? Cut it or make it specific.
29. **Statistics cohesion.** Does each test or dataset get its own paragraph opening
    with what it checks in plain words, before the numbers?
30. **Cross-references resolve.** Every named artefact, panel, dataset, or prior
    result is defined on first use or linked to where it lives. "The prior 84.2%
    result on the 38-item editorial panel" tells a reader nothing if neither the
    panel nor the packet is named anywhere.
31. **Internal pointers name their target.** "In the references", "see the docs",
    "as documented elsewhere" point at nothing. Name the file and the section, and
    link it, the way an external citation would be named.
32. **Numeric precision matches the measurement.** Five significant figures on a
    single run of a single machine claims a stability the method cannot support.
    Round to what the measurement earns, or state the spread.
33. **Hollow spans flagged, not filled.** Prose that makes no claim was flagged for
    the writer rather than reworded into something that sounds like one.
34. **Recap-flattery and wall-of-text.** In replies: no opener that praises or
    paraphrases the question, and no paragraphing that hides a sequence the reader
    needs.

## C. Fidelity

35. **Scripted check run, not eyeballed.** `slopscore.py --fidelity` exits zero.
36. **No invented specifics.** No number, name, anecdote, date, or source appeared
    that the author did not supply.
37. **No invented interior claims.** No stated feeling, motive, or experience the
    author never wrote.
38. **Qualifiers survive.** Hedges, scope limits, and caveats carry the same strength
    as the source.
39. **Claims not reframed.** Same names and numbers can still carry a changed
    emphasis or implication. Compare meaning, not tokens.
40. **Non-prose untouched.** Code, front matter, tables, blockquotes, identifiers,
    paths, and heading hierarchy intact.

## D. Voice and readability

41. **Expert voice.** A respected practitioner sounds at home: precise terms used
    correctly, authority earned through specifics, no hedging into mush.
42. **Followability.** A smart first-time reader follows each sentence on the first
    pass. One idea per sentence; every abstraction anchored in the same breath; never
    three or more abstract noun phrases stacked.
43. **Voice preserved.** Would the writer recognize this as theirs? Distinctive
    vocabulary, cadence, bluntness, humor, uncertainty, and digressions survived.
44. **Strong sentences left alone.** Nothing was rewritten merely for consistency.
45. **Active voice with human subjects.** People do the verbs. Passive stays only
    where the actor is unknown, irrelevant, deliberately withheld, or native to the
    genre.
46. **Proportional cutting.** No compression that stripped character. Density is
    information per word, not fewer words.
47. **Read aloud.** Would this sound natural read to a sharp colleague?
48. **No over-correction.** AI slop was not traded for edgy slop: forced hot takes,
    fake first person, performed candor, staccato drama.

## E. Form

49. **Returned in the format it arrived in.** A .docx comes back a .docx.
50. **Reader language.** No evaluator or harness vocabulary leaked into the copy:
    candidate, artifact, overlay, gate, scorecard, burstiness.
51. **Formatting slop.** No emoji headings, decorative bold, bullets that should be
    prose, or headers over two-sentence sections.
52. **Em dashes.** None in short copy. One or two in a long draft only where they
    clearly beat a comma, period, or parenthesis.
53. **Attribution accurate.** The report names who did what without guessing which
    model is running, and never implies a Zero Slop service read the draft.

## F. Process integrity

Role 8 answers this section. It is the check no single-agent eval can make.

54. **Roles stayed separate.** The copy desk, read-aloud pass, verification, and
    fresh-eyes review each ran as a distinct pass.
55. **No self-certification.** No role graded text it generated.
56. **Counts reported.** Every count in section A appears in the summary, including
    the zeros.
57. **The exact final text cleared every check.** Not an earlier draft, not a version
    that was repaired afterward.
58. **Role 8 approved without changes.** If it changed anything, roles 5 through 8
    ran again on the revision.
59. **Fallbacks named honestly.** If the three-round limit was reached, the report
    says which check failed and does not describe the result as fully verified.
