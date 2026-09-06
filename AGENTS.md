# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, OpenCode, Warp, etc.)
working in or executing this repository.

## What this repo is

A portable agent skill. The runtime artifact is `SKILL.md` (YAML frontmatter
+ the detect → rewrite → verify → learn loop). `scripts/slopscore.py` is an
optional heuristic surface scorer — stdlib-only Python, offline, read-only. There
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
  reviewed shared rules merge over base at runtime. Private online learning
  lives under `$ZERO_SLOP_HOME` (default `~/.zero-slop`) and loads last, so an
  install or update never overwrites it. `data/learned-log.md` is the dated log
  of reviewed shared taxonomy changes.
- No trained model ships. One was built and cut for being confidently wrong on
  current-era text; `references/evidence.md` documents that negative result.
  Do not reintroduce a trained channel without a transfer test on drafts from
  the model generation users actually face.
- `scripts/contextual.py` is a maintainer-only release-research tool. It prepares and
  validates source-bound host-model reviews, never calls a model, and never changes
  production output or the surface score. It is deliberately excluded from the
  packaged skill; Zero Slop has one production workflow and no runtime feature switch.
- `scripts/learn.py --guide --for <draft>` retrieves reason-labelled private fix
  preferences. Retrieval is advisory lexical coverage, not a probability, and must
  abstain when no relevant evidence exists.
- `$ZERO_SLOP_HOME/voices/` — private named scoring profiles, outside the
  repository. The sample-based builder records an existing lexicon or rider
  term after one exact word match. It does not store the sample or model the
  writer's full style, and the profile has no effect unless selected with
  `--voice NAME`. Never commit these profiles.
- `$ZERO_SLOP_HOME/notes.json` — a run counter and one boolean, so the single
  GitHub-star note can be shown once and never again. It records no text, no
  scores, no paths and no identifiers, is never sent anywhere, and the note is
  suppressed entirely by `ZERO_SLOP_NO_NOTES=1`, by `--json`, `--batch` or
  `--gate`, and by any run whose stdout is not a terminal.
- `bench/` (if present) — reproducible benchmark harness and scorecard.
- `website/` is a retained, testable snapshot, not the source of the live site.
  Its deploy command intentionally refuses. The live site at `zero-slop.ai` is
  built from `github.com/manavmishra/ZSWebpage`; make and deploy site changes
  there. Do not remove the refusal guard or deploy this snapshot to
  `zero-slop.ai`. Identify production by its domain, not its palette: the colour
  named here went stale the day the site was repainted.

## Maintenance contract

- Reviewed shared tells go in `data/learned.json` with a dated line in
  `data/learned-log.md`. Private reflect-loop tells and false-positive overrides
  stay under `$ZERO_SLOP_HOME`; never copy them into the repository without the
  explicit export, review, and merge path.
- `package.json` is the release version. `SKILL.md`, `README.md`,
  `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `plugin.json`,
  `gemini-extension.json`, and `server.json` bump with it. Run
  `python3 scripts/check_distribution_manifests.py` before publishing.
- A packaged runtime change requires a new version. After validation passes on
  `main`, `sync-release.yml` creates the matching tag and dispatches the GitHub
  release and official MCP Registry jobs. npm publishes from the same commit.
  The separate website repository then imports and verifies that release; its
  hourly reconciliation is the no-secret recovery path.
- `package.json` publishes the skill to npm for registry discovery. Its `files`
  allowlist must ship exactly what `scripts/build_plugin.py` mirrors into
  `skills/zero-slop/` — same runtime, same exclusions. When you add or remove a
  maintainer-only script, update `EXCLUDE` and the `!` negations together, then
  confirm with `npm pack --dry-run`.
- Every regex must compile under Python `re` AND stay JS-compatible where
  possible (the data files are consumed as inert JSON by other tooling).
- Run the validation used in CI before publishing:
  `python3 -c "import json; json.load(open('data/patterns.json'))"` and the
  scorer smoke test in `.github/workflows/validate.yml`.
- Security posture in `SECURITY.md` is a contract. Runtime scripts never transmit
  drafts; the optional version check is the sole metadata request.
  Runtime writes are limited to explicit outputs, `$ZERO_SLOP_HOME`, and the
  maintainer-only shared merge/calibration paths. Do not add `eval`, `exec`,
  pickle, or subprocess execution to runtime scripts.
- Corpora are admitted by `bench/corpus-registry.json`. Match every evaluation to
  the semantics of its labels; provenance corpora never become slop-quality accuracy
  by proxy.
