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
