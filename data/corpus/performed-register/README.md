# performed-register — should-flag corpus

Thirty-five spans a human editor flagged as slop on sight while the scorer
passed every one clean (9.5–10.9, zero pattern hits). All come from
zero-slop.ai blog drafts written in August 2026 — first-party text, so no
external registry entry applies. They share one register: **performed-writer
prose**, an AI imitating a punchy human writer. The taxonomy rows live in
`references/tells.md` §3; the rewrite-side ban is `references/overcorrection.md`.

These are register labels from one human editor, not authorship labels and not
a benchmark. They exist so calibration and regression runs exercise the misses
that motivated v2.5.6.

## Layout

- `mechanical/` — one span per file, each of which must draw at least one
  pattern hit from `data/patterns.json`. The unit test
  `Detector.test_performed_register_corpus_is_caught` fails if any goes
  silent again, so a pattern cannot be weakened or deleted without noticing.
- `judgment/` — spans whose literal forms are legitimate in news, history,
  crime, or science writing, so no regex gates them safely: staccato
  antithesis pairs ("Not perfect. Honest."), bare subject swap ("Llama is
  open-weights. Dolma releases the data."), extended conceits (forensics,
  courtroom, billing, recipe), chiasmus, one-word drama beats ("Fine."),
  jargon compression ("threshold cliff"), and campaign taglines ("the fight
  against slop" — rider-gated, silent without a marketing trigger). The
  performed-register pass in SKILL.md's diagnose and read-aloud briefs owns
  these; a regex that would catch them fires on the must-not-flag corpus,
  which wins every conflict.

**Files move in both directions.** `judgment/` is a record of what no *current*
safe rule reaches, not a permanent verdict. In v2.5.10 `verdict-arithmetic.txt`
("Most AI-writing tools hand you a verdict. The slop score hands you
arithmetic.") graduated to `mechanical/` when `isocolon-ditransitive` reached it
without touching a single must-not-flag file. When that happens, move the file,
add the dated line to `data/learned-log.md`, and say in the log what safety
property made the rule admissible — for that one, a backreference pinned to the
verb, which rhetorical anaphora never repeats.

## Rules

1. `data/corpus/must-not-flag/` outranks this directory. A candidate pattern
   that silences a file here but fires on any must-not-flag sample is
   rejected; move the span to `judgment/` instead.
2. Keep spans verbatim as the editor flagged them; they are evidence, not
   templates.
3. New performed-register misses get a file here plus a dated line in
   `data/learned-log.md`.
