# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, OpenCode, Warp, etc.)
working in or executing this repository.

## What this repo is

A portable agent skill. The runtime artifact is `SKILL.md` (YAML frontmatter
+ the detect → rewrite → verify → learn loop). `scripts/slopscore.py` is an
optional statistical scorer — stdlib-only Python, offline, read-only. There
is no build step. Keep all wording harness-neutral: Claude Code and Codex
are examples, not limits.

## Executing the skill

1. Read `SKILL.md` fully; it routes you to `references/` by genre and task.
2. Run the scorer when `python3` exists: `python3 scripts/slopscore.py
   --explain <file>` (or stdin). **If python3 is unavailable, degrade
   gracefully**: skip the metered gate, use `references/tells.md` +
   `references/overcorrection.md` and the self-rubric in SKILL.md step 4 as
   the gate. Never fail the task because the scorer can't run.
3. The hard rules in SKILL.md (no fabrication — including interior-experience
   claims; flag hollow spans; no over-correction) are non-negotiable in every
   harness.

## Key files

- `SKILL.md` — source of truth for behavior.
- `data/patterns.json` + `data/learned.json` — the weighted tell database;
  learned merges over base at runtime. `data/learned-log.md` — dated log of
  every taxonomy change.
- No trained model ships. A MaxEnt classifier was built and cut for being
  confidently wrong on current-era text; `references/evidence.md` documents
  that negative result along with the SVM and HMM rejections. Do not
  reintroduce a trained channel without a transfer test on current drafts.
- `data/voices/` — per-user voice profiles. Git-ignored, personal, never
  commit.
- `bench/` (if present) — reproducible benchmark harness and scorecard.

## Maintenance contract

- New tells go in `data/learned.json` with a dated line in
  `data/learned-log.md`. Pattern-weight fixes for false positives go in
  `data/patterns.json` (learned patterns append; they cannot override).
- `SKILL.md`, `README.md`, `.claude-plugin/plugin.json`, and
  `.codex-plugin/plugin.json` versions bump together.
- Every regex must compile under Python `re` AND stay JS-compatible where
  possible (the data files are consumed as inert JSON by other tooling).
- Run the validation used in CI before publishing:
  `python3 -c "import json; json.load(open('data/patterns.json'))"` and the
  scorer smoke test in `.github/workflows/validate.yml`.
- Security posture in `SECURITY.md` is a contract: no network calls, no
  subprocess, no eval, no writes outside `data/` learning files. Do not add
  code that violates it.
