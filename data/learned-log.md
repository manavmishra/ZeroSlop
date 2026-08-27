# Learned-tell log

- 2026-08-03 — Benchmark failure mode caught by a blind judge: one rewrite
  (AWS-exam LinkedIn post) added an interior-experience claim ("by test day
  the real thing felt familiar") absent from the source. Hard rule 1 in
  SKILL.md now names experiential/interior claims as fabrication explicitly.

One line per change to `learned.json` or `patterns.json`: date, what, why,
example that motivated it.

- 2026-08-25 — v2.5.8. Added `generic-benefit-stack` (weight 1) after the
  frozen quality panel exposed five passages whose product noun and multiple
  interchangeable outcomes passed below the gate. The rule requires a
  product or service, an offer/help verb, and two nearby generic outcomes;
  a lone word cannot fire it. It moved five sloppy consensus
  items above the gate, changed no clean consensus item, and kept all 13
  known-human safety files below 25. The local scorer now indexes vocabulary
  by first character and caches compiled patterns. A 280-document parity run
  found no change from that optimization, while an alternating six-pair run
  against v2.5.7 measured a 29.4% median throughput gain.

- 2026-08-25 — v2.5.7. Audited JCarterJohnson's 89,239-post reader-salience
  study and `unslop-ai-text` at commit
  `f7c4aefc2c797a66e55b49354a93917ab60d33ac`. Zero Slop already covered all
  25 published categories, so no regexes, weights, or blanket em-dash rule
  were imported. Added a meaning-first review order and three judgment-only
  checks: reflexive agreement, communicative drift, and rhetorical scale
  mismatch. Added manufactured informality to the overcorrection guard. The
  upstream scanner called the 13-file known-human safety set "strong" based
  on three high, two medium, and one low finding; Zero Slop kept all 13 below
  its gate. Fixed `--batch --json` so CI receives JSON while preserving the
  gate exit code, and added unslop-text to the pinned capability audit. These
  comparisons test false-positive safety and documented features, not which
  editor produces better prose.

- 2026-08-24 — v2.5.6. Performed-writer register: a human editor flagged 35
  spans from the zero-slop.ai August blog drafts that the scorer passed clean
  (zero pattern hits) — theatrical process framing ("Then we hired an
  adversary"), epigram payoffs ("turns out to carry an expensive signal"),
  staccato antithesis ("Not perfect. Honest.", "Slop isn't a vibe. It's
  measurable."), metaphor flourishes and extended conceits ("the other half
  lands on the sender's name", "rhythm leaves prints", "never allowed to
  convict", "opens the hood"), slang-cute idioms ("it has receipts", "vibe
  check"), hyperbole ("nothing on earth scores a perfect zero"), one-word
  drama beats ("Fine."), jargon compression ("threshold cliff",
  "length-blind floor"), and cute meta-taglines ("a writing meter you can
  argue with", "the fight against slop"). Added twelve conservative patterns
  (w 2–2.5, cat `performed`): `hired-adversary`, `turns-out-payoff`,
  `has-receipts`, `hyperbole-universal`, `argue-with-artifact`,
  `vibe-register`, `where-x-lives`, `billed-conceit`, `on-the-tin`,
  `minding-own-business`, `economics-brutal`, `opens-the-hood`, plus rider
  "fight against" (fires only beside a marketing trigger, so history and
  civic prose stay silent). Spans no regex gates safely became judgment-pass
  rows in tells.md plus a named performed-writer check and a statistics-
  cohesion rule (one test per paragraph, plain-words setup before numbers) in
  SKILL.md's diagnose and read-aloud briefs; the family is cross-referenced
  with overcorrection.md as the meter-side twin of edgy-slop. All 35 spans
  now live in `data/corpus/performed-register/` — the 16 mechanically
  catchable ones are regression-tested
  (`test_performed_register_corpus_is_caught`), the 19 judgment-only ones are
  the read-aloud fixture list. Must-not-flag corpus 12/12 with zero new hits;
  search-corpus, RAID+, and Beemo audits re-verified with identical numbers.
  In the historical 50-draft chart panel, `billed-conceit` fires on one
  humanizer and one stop-slop rewrite ("the cost/bill lands on"), nudging
  those two competitor means up 0.2 (20.5→20.7, 16.7→16.9) — the meter
  catching the conceit those tools injected. Every published Zero Slop
  number stands; the detector chart was regenerated.

- 2026-08-22 — AIStoryHub Corpus of AI Clichés v1.8 coverage audit. Fixed a
  detector-ordering bug that erased `utm_source=chatgpt.com` before the
  existing artifact rule could see it; added the `attributableIndex` and
  stand-alone “Regenerate response” paste artifacts; and expanded strict
  bracketed placeholders such as `[Company Name]`, `[Recipient]`, and
  `[Date]`. Ambiguous vocabulary and persona names remain context-gated or
  unscored to protect the must-not-flag corpus.

- 2026-08-03 — Prompt-engineering review (Prompeteer THE SEED): added
  `--formal` scorer mode; formal-genre verify gate; corrected learned.json
  override semantics; de-em-dashed the LinkedIn worked example; scoped the
  ≥3-claims rule to author-supplied material.
- 2026-08-03 — Initial release. Base taxonomy seeded from WP:AICATCH,
  de-slop/stop-slop detector line, petergyang/no-ai-slop, blader/humanizer
  v2.9.1, and the Kobak/Liang/Juzek lexicon studies. Calibrated on a
  50-draft AI corpus (mean 76/100) vs human exemplars (9–29/100).
- 2026-08-03 — First live run (Manav's enterprise-AI-reports LinkedIn post):
  scorer missed the "has too often" announcement-voice opener and the "says
  the quiet part out loud" cliché; both added as learned patterns. Voice
  profile created at data/voices/manav.md.
- 2026-08-03 — User feedback (Manav): hook attributed OpenAI's 6x stat to
  "two new reports" and never paid off the second — "feels amnesiac". Added
  a source-scope check to the verify rubric in SKILL.md (judgment-level; no
  regex can see it). Voice profile updated: when citing multiple reports,
  each gets called out with its own number.
- 2026-08-03 — User feedback (Manav): a paragraph of four consecutive
  clipped declaratives read as robotic — the staccato over-correction
  overcorrection.md already names, produced by this skill's own rewrite.
  Lesson: the punchy register is for hooks and landings, not analytic
  middles; those want subordinated, flowing sentences (NYT-editor cadence).
- 2026-08-03 — Round-2 benchmark (vs stop-slop and the stacked
  no-ai-slop→humanizer pipeline): the two-pass pipeline tied/edged the
  single-pass loop (8.03 vs 8.00 composite; LinkedIn 11-9). Architecture
  lesson encoded: step 3 is now explicitly two passes (Strip, then Build)
  with an anti-over-cutting guard. stop-slop's 27 worst-picks confirm the
  guard: most-aggressive surface removal ≠ best writing.
- 2026-08-03 — False positive: lexicon "harness" (w 2.5) fired on "agent
  harness", standard technical usage in agent-tooling prose. Lowered to 1.0
  in patterns.json per the override rules.
- 2026-08-03 — v1.1 validation: two-pass architecture wins the LinkedIn
  pairwise blind head-to-head 15-10 vs the stacked no-ai-slop→humanizer
  pipeline (v1.0 had lost that genre 9-11). Caveat kept honest: all 15 wins
  narrow; the pipeline took the 4 clear-margin verdicts.
- 2026-08-03 — User feedback: skill output was "dense, hard to follow, not
  insightful" — technically clean prose that chained five abstractions in
  one sentence. New failure mode named: compression ≠ writing. Added a
  followability channel to the scorer (comma-chain fraction, long-word
  ratio, 38+-word sentences; formal genres exempt), a followability gate to
  the verify rubric, a density-ceiling rule to the expert-voice mandate,
  and a live before/after to rewrite-moves L1. The criticized paragraph now
  fails the gate (28.2); its unpacked rewrite passes (9.5).
- 2026-08-03 — Second followability iteration, same paragraph: the first
  fix swapped abstraction-chains for an unexplained metaphor ("finishing
  school") plus an inside-baseball citation list — decoding load moved,
  not removed. Rule sharpened: a metaphor anchors only when its mapping is
  set up first; otherwise it's compression in costume. Prefer a plain
  comparison the reader can picture. Name-lists of papers belong in the
  citation file, not the prose.
- 2026-08-03 — User feedback, three lessons encoded together: (1) the loop
  description read as spec-notation (arrows, threshold dumps) rather than
  writing — "arrow-in-prose" and "threshold-dump" added as learned scorer
  patterns; (2) fixing one paragraph isn't the standard — a
  whole-document-consistency check added to the verify gate (uniform
  register, cross-references must resolve); (3) the correction must not
  overcorrect: "everything shouldn't be prose" — the gate now reads "form
  follows context": structured content (lists, tables, diagrams, spec
  blocks) stays structured, and each form is held to what a skilled human
  author would produce in that form. Step 0 gains a form inventory.
- 2026-08-03 — Product requirement from live use: every run must end with
  a before/after scorecard (fixed table shape: surface score + band,
  weighted tells, formatting counts, burstiness, followability, words,
  gate verdict, facts-preserved count). Encoded as a template in SKILL.md
  step 5; no longer left to the executing model's formatting judgment.
- 2026-08-03 — v1.2 benchmark run surfaced a gap: a draft asserted "~70% of
  enterprise AI pilots never reach production" with no source. The correct
  handling (keep as the author's claim, flag it, never invent a citation and
  never launder it into "studies show") was previously implicit. Now an
  explicit verify-gate rule. Same run: 25/25 LinkedIn gate passes,
  followability 0.000 on every post, and the executing agent removed its own
  invented specifics in the final pass — the fidelity rules holding under a
  model that had already drafted the text.
- 2026-08-03 — Replication finding, the most important of the project: a
  second blind judging pass on the identical 50 rewrites moved Zero Slop's
  best-picks from 32/50 to 23/50 (64% to 46%). Cohen's kappa 0.12 means
  judges barely agree on "best". Pooled 55/100 beats a 25% chance rate
  (p=1.7e-10) but is NOT separable from blader/humanizer head-to-head
  (p=0.15). All published claims corrected. Methodological rule for any
  future benchmark run by this project: never publish a single-pass judge
  number without a replication and an agreement statistic.
- 2026-08-03 — Adversarial red-team (36 tool-uses, 779-line report). Six
  vulnerabilities found and fixed in the scorer: (1) regexes were
  contraction-locked, so expanding "it's" to "it is" dropped 20-tell slop
  from 100 to 9.5 while the skill's own L4 rule told rewriters to ADD
  contractions — 18 patterns now match both forms; (2) inline `code` spans
  were stripped, so backticking slop hid it — only the backticks are removed
  now, the words are scored; (3) tell density was length-normalised without
  bounds, so 20 tells diluted to a pass at 2437 words and one tell in a
  7-word tweet scored 100 — window floored at 60 words with an absolute
  weight term; (4) the skill's own banned edgy-slop (overcorrection.md) was
  invisible to the scorer — four overcorrection patterns added; (5) the
  em-dash term was uncapped, convicting the Gettysburg Address at 88.9 —
  capped, and (6) formatting/register penalties now require lexical
  corroboration, implementing the "clusters convict, singles don't" rule the
  scorer stated but never enforced. Gettysburg 88.9 → 29.6, evasions all
  restored to ~100, corpus calibration held (37/50 flagged, v1.2 50/50 clean).
  Still open and documented as boundaries: hollowness remains invisible to
  any regex (by design), non-Latin scripts score unconditionally clean, and
  the learning loop must never lower a weight to pass the draft under review.
- 2026-08-03 — Running the skill on its own README caught two false positives
  in patterns added earlier the same day: "arrow-in-prose" fired on UI menu
  paths (Settings → Capabilities → Skills) and "question-hook-opener" fired
  on bolded FAQ headings. Both are correct forms, not tells. Fixed: the arrow
  rule now requires lowercase on both sides via (?-i:) — necessary because
  the scorer matches case-insensitively, so a plain [a-z] class silently
  matched capitals — and the question rule exempts markdown-bold headings.
  README prose went 30.3 → 20.9 after stripping six em-dashes from running
  prose; the raw file still scores 99.9 because it quotes the tells it
  teaches, which is the documented mention-versus-use boundary.
- 2026-08-03 — Cut the trained detection channel and its 205 KB of weights.
  It scored 0.985 AUC in-domain but failed the only test that mattered: on
  2026-era drafts it rated real AI slop as human (mean p=0.038), and a live
  check returned p=0.33 for text the pattern meter scored 100/100. A channel
  that is confidently wrong on current text is a liability even when labelled
  a second opinion. The interpretable channels carry the signal on their own,
  and every point of the score still traces to a quoted span. The negative
  result is documented in references/evidence.md; other classifier families
  were rejected earlier on the same evidentiary standard.
- 2026-08-03 — Answered the "hardcoded meter" problem with three mechanisms
  instead of a bigger list. (1) calibrate.py derives lexicon weights from
  excess frequency between a human corpus and current AI output, so the meter
  can be re-fit to any model generation or to one writer's baseline.
  (2) data/corpus/must-not-flag/ is a false-positive regression suite;
  calibrate.py --selftest must pass before any pattern change ships. It
  immediately caught three real bugs: duplicate lexicon prefixes double-
  counting one word (elevate/elevat), technical terms of art convicting
  honest prose (robust, landscape, elevated), and style-only conviction of
  text with zero lexical evidence. (3) Rider words are now sentence-scoped:
  13 context-dependent terms score only when a marketing-register trigger
  shares their sentence. Result: 6/6 on the FP suite, marketing use of the
  same words still scores 100, corpus calibration unchanged at 37/50 flagged
  and 50/50 clean. Patterns also gained first_seen/last_confirmed with an
  18-month decay so stale tells fade automatically.
- 2026-08-03 — User rule: the output format must match the input format.
  Text in, text out; .docx in, .docx out; PDF in, PDF out; a file in a repo
  is edited in place so the diff is reviewable; a JSON field comes back as
  that field. Non-prose content (front matter, code, tables, links, merge
  fields, markup) survives untouched, and the skill must never silently
  downgrade to markdown — if it cannot produce the input type it says so.
  An explicit request for a different format overrides. Encoded in step 0
  (record the input format) and step 5 (a format-matching table).
- 2026-08-04 — Shape channel added after a verified blind spot: paragraph
  structure was flattened before scoring, so the same words in 26 paragraphs
  or 1 scored identically to the decimal. Broetry was invisible, and worse,
  its fragment/long mix INFLATED burstiness — the channel meant to catch
  machine cadence was satisfied by the tell. A naive fix would also have died
  at the corroboration clamp, which caps stylistic evidence at 3.5 exactly
  when zero lexical hits are present, the common broetry case.
  Built corpus-first: data/corpus/must-not-flag-shape/ holds six genres that
  mimic broetry (poem, dialogue, changelog, SMS, aphorisms, lyrics), all
  solo_frac 1.00, so a naive metric convicts them harder than the real thing.
  Guards run before the metric (structural markers, dialogue openings,
  eight-paragraph floor) and silence five of six; lyrics remains a documented
  boundary rather than a special case. Reported as its own axis, never folded
  into ai_likelihood, because broetry is a slop tell not a machine tell and
  the reach-versus-voice call belongs to the author.
  Also fixed the deeper failure: the gate printed PASS for channels it never
  measured. Every verdict now enumerates what was checked and what was not.

- 2026-08-04 — Reflect loop added 2 context-gated rider(s) (capability, experience) after each was struck from 5+ documents. Entered as riders, not always-on lexicon terms.

- 2026-08-04 — Reflect loop promoted 0 pattern(s) after each was independently cut from 3+ documents (); 0 rejected by the false-positive gate. Source documents are not recorded: reflection evidence stays on the machine that produced it.

- 2026-08-04 — Community taxonomy review (r/OpenAI "telltale signs of AI-slop writing" thread and adjacent write-ups). Coverage test over ten named tells: eight already caught. Added lexicon term `ascertain` (w 3) and pattern `thats-the-thing` (w 3). Deliberately NOT added: the rule-of-three tricolon. It is a named AI tell and also standard rhetoric; the 12-sample corpus is too small to certify a pattern that broad, and shipping it would risk convicting honest parallel construction. Revisit when the corpus is larger.

- 2026-08-04 — Community taxonomy pass over the r/OpenAI "telltale signs of
  AI-slop writing" thread (Apr 2025, 78 comments). Tested the ten tells named
  by the post and its commenters; four were already caught. Added six:
  `fragment-question-pivot` (w 5) for the noun-phrase drum-roll question
  ("The kicker?", "The issue?", "The real issue?") — the single most-cited tell
  in the thread, quoted by four separate commenters and previously scoring 9.5,
  the floor; `theres-a-twist` (w 4); `not-only-but-also` (w 3);
  `explainer-restatement` (w 3.5) for the sentence that restates the paragraph
  it ends, named by a working editor as "the unnecessary explainer sentence";
  `tacked-on-moral` (w 4) for the lesson appended whether or not the piece
  earned one. Every one cleared the 12-sample must-not-flag corpus. The
  fragment-question regex is anchored to a sentence boundary and requires the
  answer to follow, so an ordinary question is untouched.

  Deliberately not added, though named in the thread: the em-dash as such
  (density is already scored, and two commenters in that same thread are
  career writers who have used em-dashes for twenty years — a per-instance
  rule would convict them); "consistent hyphenation"; and the rule-of-three
  tricolon, which is a real AI tell and also standard rhetoric that a
  12-sample corpus is too small to certify a pattern against.

- 2026-08-04 — False-positive measurement against genuine human technical prose:
  5 of 8 human-written documents in this repo were convicted at the ≤25 gate.
  Two causes, both fixed. The corroboration floor was 0.45, handing style 45% of
  its weight on text with no lexical evidence at all, and the clamp keyed on hit
  *count* rather than weight, so a single weight-2.5 hit unlocked the full
  em-dash penalty — AGENTS.md scored 59.2 on one arrow in 392 words. Floor is
  now 0.10 and the clamp is weighted (density < 1.5).

  Separately lowered `arrow-in-prose` 2.5 → 1.0. It fires on ordinary pipeline
  and mapping notation ("read → transform → write", "id → record"), which is
  correct technical writing, and at 2.5 it was on its own enough to push honest
  prose past the gate. This is a weight change motivated by false positives
  across several documents, not by one draft failing — the distinction step 6
  requires.

- 2026-08-15 — v2.3.0 research pass. A 20-source sweep (current WP:AICATCH,
  Kobak's July-2025 ~900-word excess-vocab update, Juzek & Ward's RLHF-cause
  papers, The Economist's 1.2M-word measured study, tropes.fyi, and
  LinkedIn's own reach-penalty data) cross-checked against the day-old
  coverage release: the big families all held, 17 gaps closed ("That's
  where X comes in", the WP "despite challenges / future outlook" formula,
  "not all X are created equal", counting preambles, false-vulnerability
  hooks, "quietly reshaping", metaphor-of family), vendor paste-debris
  extended to Gemini/Grok/Perplexity markers, and 5 lexicon + 4 rider
  terms added. Notable calibration facts recorded from the sweep: LinkedIn
  measures "Stop X. Start Y." as its steepest reach penalty (−6.7%) and
  "It's not X, it's Y" at −4.9%; The Economist found only Claude-family
  models over-use em-dashes (ChatGPT uses fewer than humans) — supports
  keeping the em-dash term capped and corroboration-gated rather than
  raising it; and construction tells persist across model generations
  while word tells churn — which is the decay mechanism's design premise.
  Gates: 12/12 corpus, zero drift on all 16 human docs, mean AI-draft
  score 77.1, recall steady at 47/50.

- 2026-08-14 — v2.3.0, the coverage release. A 260-sentence audit battery of
  tells named by WP:AICATCH, community taxonomies, and the detector-line
  repos found 260 with ZERO pattern hits — including six variants of the
  contrast family the skill already claimed to catch: "Success isn't about
  talent. It's about consistency." (generic subject), "It's not just a
  tool—it's a partner." (em-dash separator), and "It is not about speed; it
  is about direction." (expanded contraction — the exact contraction-lock
  bug the 2026-08-03 red-team fixed elsewhere, reintroduced in the newest
  patterns). Fixed the four contrast regexes (any subject, any separator,
  both contraction forms), extended fragment-question-pivot's noun set
  (part/news/takeaway/lesson/mistake…), and added 175 patterns across
  families that had no regex at all: fake epiphany ("that's when it hit
  me", "little did I know"), certainty theater ("cannot be overstated",
  "Full stop."), non-conclusions ("only time will tell"), manufactured-world
  openers ("Gone are the days", "In a world where"), imperative flips
  ("Stop X. Start Y."), cliché autopilot (double-edged sword, tip of the
  iceberg, elephant in the room — low weights, shared with humans, clusters
  convict), chatbot residue ("Would you like me to", "my training data"),
  form-letter email, LinkedIn ritual ("some personal news", "today years
  old"), and DM-funnel engagement ("comment X and I'll send"). Plus 36
  lexicon terms (whopping, unsung→pattern, skyrocket, picturesque,
  garner and bolster — named in tells.md since v1 but never implemented)
  and 8 riders (emphasiz/enhanc/highlight per the 2025+ era-shift note).
  Every addition cleared the 12-sample must-not-flag corpus with zero score
  movement on any sample (checked to the decimal, not just under-gate), and
  zero movement on this repo's own human docs. Coverage on the battery went
  260 misses → 3, all deliberate ("no silver bullet", "eat our own dog
  food" — genuine engineering idiom stays legal). Benchmark recall: 37/50
  → 47/50 AI drafts flagged; human corpus range unchanged at 9.5–20.2.
  ReflectLoop test fixtures moved off "moves the needle" because the meter
  now catches it — the novelty gate correctly refused to re-mint it, which
  is the learning loop working as specified.

- 2026-08-04 — v1.5.0. Fidelity became a measured channel rather than a rule
  the agent was asked to honour, closing the one dimension the benchmark ranked
  the skill last on. False-positive rate on ordinary human prose went from 5-in-8
  to 0-in-5 after two scoring bugs were found by measurement: a corroboration
  floor of 0.45 that gave style 45% weight with no lexical evidence, and a clamp
  keyed on hit count so a single weight-2.5 tell unlocked the full stylistic
  penalty. Six community tells added, `--explain` and `--json --gate` repaired,
  `--dna` added, a ReDoS and two quadratics removed, and user prose stopped
  reaching git-tracked files.
- 2026-08-26 — v2.5.9 incumbent audit. Added three precision-scoped shared
  patterns from `conorbronsdon/avoid-ai-writing@40328bd`: noun-anchored
  lingering-attention framing, generic social endorsement closers, and
  asterisked chat-roleplay actions. Literal return-to-an-idea clauses with a
  reason, ordinary instructional verbs, and ordinary italics stay silent.
  Expanded the existing AI-tool residue rule to cover tracker parameters from
  Claude, Copilot, Gemini, Perplexity, and Grok. Added mixed-script and
  zero-width normalization, exact protection for
  code/front matter/blockquotes/tables/inline identifiers/paths/heading levels,
  and a weak long-form low-word-variety check. The latter was the only new
  stylometric feature to clear the incumbent's 1,654-paragraph corpus with
  useful lift (20/779 machine paragraphs, 1/875 human; 22.46x). Function-word
  entropy, punctuation uniformity, and cross-paragraph rhythm were tested but
  did not fire on the 38-item editorial panel; they remain unshipped. Frozen
  editorial metrics were unchanged, 12/12 known-human files stayed below the
  gate, and the adversarial fixtures moved from missed to caught.
- 2026-08-26 — v2.5.10 unmarked-antithesis gap. A 209-word draft with four
  antithesis pairs, one per paragraph, scored 13.0/100 "clear" with zero flagged
  phrases. Root cause: all 17 `contrast` patterns were anchored on a literal
  negation token (`not`, `n't`, `never`, `won't`), so the same figure with no
  marker was unreachable, and the pairs' short-then-long cadence *raised*
  burstiness from 0.332 to 0.527 — the tell paid off the channel built to catch
  machine cadence, the failure mode already documented for broetry. Added three
  patterns and widened one: `isocolon-ditransitive` (a give-you frame whose verb
  repeats across a sentence break), `this-is-what-looks-like`,
  `no-x-had-to`, and eight nouns on `performed-candor` so "Here's the detail
  that matters" is caught. The draft moved 13.0 → 59.0.
  `isocolon-ditransitive` is the first pattern to reach a figure rather than a
  phrase; its safety property is that the backreference sits on the **verb**,
  which anaphora never repeats ("dedicate / consecrate / hallow"). Three
  frame-level loosenings were measured firing on `gettysburg.txt`,
  `federalist.txt`, and `esl-engineer-email.txt` and were rejected;
  `Detector.test_isocolon_rule_turns_on_verb_identity` pins that. All 114 frozen
  document scores were unchanged, 18/18 known-human controls stayed below the
  gate, and blind-panel accuracy held at 0.8421. These are the file's first
  patterns to carry `hints`, which left throughput higher than the baseline.
  `judgment/verdict-arithmetic.txt` graduated to `mechanical/` — the first span
  to move from "no regex gates this safely" to caught. Bare subject swap
  ("Llama is open-weights. Dolma releases the data.") stays unreachable and was
  added as `judgment/bare-subject-swap.txt`; SKILL.md now makes the
  performed-register pass mandatory and gives it a reported count, because a
  clean scorer had been licensing the assistant to skip it entirely.

- 2026-08-26 — incumbent completeness follow-up. Added four narrowly bounded
  phrase families found in `conorbronsdon/avoid-ai-writing@40328bd`: leaked
  reasoning narration, unsupported novelty formulas, generic emotional
  reactions, and answer-restatement loops. Each rule names the full formula;
  ordinary step-by-step instructions, literal staffing statements, explained
  surprise, and direct answers remain silent. The accompanying AI review now
  checks six context-dependent problems that are unsafe to infer from a phrase
  alone: paragraph-order dependence, unsupported novelty, self-labelled
  significance, moral-adjective category errors, recap-flattery, and
  wall-of-text replies.
