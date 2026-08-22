# Rewrite Moves — the positive program

Removing tells makes text neutral. These moves make it human. Ordered by the
evidence ladder (L1 strongest detection signal + reader value).

Before using the ladder, choose the smallest effective intervention for each
passage: keep, repair, cut, or rebuild. Leave strong human sentences verbatim.
The ladder expands what an editor can do; it does not require every sentence to
be rewritten.

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
- **Name the actor when agency matters.** "The setting was changed" becomes
  "The operator changed the setting" when the source identifies the operator.
  Keep passive voice when the actor is unknown, irrelevant, deliberately
  withheld, or expected in the genre. Passive voice is a clarity decision, not
  a standalone AI tell.
- **Hide the machinery.** Outward-facing prose should not sound like the scoring
  or editing harness that produced it. Use plain language instead: "keeps every
  fact" rather than "faithful candidate," "the version we chose" rather than
  "selected rewrite," and "the text you receive" rather than "exact artifact."
  Keep a technical term only when the reader needs that concept.
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
