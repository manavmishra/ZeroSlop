# Learned-tell log

- 2026-08-03 — Benchmark failure mode caught by a blind judge: one rewrite
  (AWS-exam LinkedIn post) added an interior-experience claim ("by test day
  the real thing felt familiar") absent from the source. Hard rule 1 in
  SKILL.md now names experiential/interior claims as fabrication explicitly.

One line per change to `learned.json` or `patterns.json`: date, what, why,
example that motivated it.

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
  a before/after scorecard (fixed table shape: AI-likelihood + band,
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
- 2026-08-03 — Cut the trained MaxEnt channel and its 205 KB of weights. It
  scored 0.985 AUC in-domain on HC3 but failed the only test that mattered:
  on 2026-era drafts it rated real AI slop as human (mean p=0.038), and on a
  live check it returned p=0.33 for text the pattern meter scored 100/100.
  A channel that is confidently wrong on current text is a liability even
  when labelled a second opinion. The interpretable channels — pattern
  meter, rhythm, followability, formatting, register — carry the signal on
  their own, and every point of the score can still be traced to a quoted
  span. The negative result is documented in references/evidence.md;
  SVMs and HMMs were rejected earlier on the same evidentiary standard.
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
