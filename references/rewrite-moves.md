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
