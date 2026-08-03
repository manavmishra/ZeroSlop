# Security posture

Zero-slop is designed to be auditable in one sitting and safe to run in
locked-down environments. The guarantees, all verifiable by reading the
source:

- **Fully offline.** Nothing in this package makes a network call. The only
  executable, `scripts/slopscore.py`, imports `json`, `math`, `re`, `sys`,
  and `pathlib` — Python standard library, nothing else. No pip
  dependencies, ever.
- **Read-only.** The scorer reads text you give it (file or stdin) plus its
  own `data/*.json` pattern files. It writes nothing, executes nothing, and
  spawns no processes. No `eval`, no `exec`, no `subprocess`.
- **Your text stays local.** Scoring happens entirely in-process. Drafts are
  never transmitted, logged, or stored by the scorer.
- **Personal data is fenced.** Per-user voice profiles (`data/voices/`) are
  git-ignored — they can never ship in the repo or a package built from it.
- **Data files are inert.** `patterns.json` / `learned.json` contain regex
  strings and numeric weights only. A malformed learned file degrades to
  base patterns rather than erroring (and can never execute code).
- **The skill instructions ask for no secrets.** SKILL.md never directs an
  agent to read credentials, environment variables, or files outside the
  skill directory and the draft being edited.

## Scope of AI-agent behavior

When run as an agent skill, the executing model follows SKILL.md, which
constrains it to: score the provided draft, rewrite it, and update the
skill's own `data/` learning files. It explicitly forbids fabricating
content, and refuses disclosure-evasion and impersonation use.

## Reporting

Found something that violates any guarantee above? Open a GitHub issue, or
email the maintainer for anything sensitive. The single-file scorer
(~200 lines) makes independent audit practical — that is a design goal.
