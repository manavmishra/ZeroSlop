# Security posture

## Runtime boundary

The installed skill ships eight standard-library Python modules:

| File | Purpose | Writes | Network |
|---|---|---|---|
| `scripts/slopscore.py` | score, heatmap, and fidelity checks | one-time interactive-note state under `$ZERO_SLOP_HOME`; never the draft | none |
| `scripts/register.py` | document-level measurements and validated final-review packets | none | none |
| `scripts/predictability.py` | create and score deterministic cloze probes | none | none |
| `scripts/rerank.py` | rank candidate rewrites | optional user-selected output | none |
| `scripts/learn.py` | private online learning, named scoring profiles, reviewed imports/exports | `$ZERO_SLOP_HOME`; shared taxonomy only through explicit maintainer `--merge --apply` | none |
| `scripts/calibrate.py` | corpus calibration and shared-pattern maintenance | explicit calibration output or shared learned data | none |
| `scripts/safeio.py` | locks and atomic file replacement | only on behalf of the two writers above | none |
| `scripts/version_check.py` | optional release check | none | one metadata-only GitHub API request |

Scoring and rewriting do not transmit the draft. The version checker sends only a GET
for the latest public release tag, times out after 2.5 seconds, fails open, and can be
disabled with `ZS_NO_UPDATE_CHECK=1`.

An ordinary interactive score may update a local counter and show one optional
GitHub-star note after the third run. That state remains under `$ZERO_SLOP_HOME`, is
never transmitted, and is skipped for pipes, JSON, batch, and gate runs. Set
`ZERO_SLOP_NO_NOTES=1` to disable it.

Build, packaging, benchmark, chart, PDF, website, and test utilities remain in the
repository but are excluded from the installed plugin runtime.
`scripts/contextual.py` is one of those maintainer-only research utilities; it is
not a production feature and cannot change a live draft or score.

## Remote MCP boundary

The optional public MCP at `https://mcp.zero-slop.ai/mcp` is a separate remote
service. A draft sent to that endpoint must leave the client to be edited. It is
processed in memory, excluded from the demo cache, and routed through model endpoints
configured for zero retention and no training. The gateway rejects any editor
response that does not confirm `stored: false`. Zero Slop does not log or retain the
draft or rewrite.

The gateway writes aggregate product and reliability events to Cloudflare Analytics
Engine. Recorded fields are limited to JSON-RPC method, tool, normalized client family
and major version, MCP protocol version, coarse country and data-center code, genre,
character and word counts, before and after scores and flag counts, result status,
completed-check counts, duration, and capacity outcome. Drafts, rewrites, prompts,
detected phrases, IP addresses, raw user agents, cookies, email addresses, and stable
user or session identifiers are excluded. Initializations are reported as connections,
not unique people. Analytics Engine retains the dataset for three months.

Telemetry writes are non-blocking and wrapped so an analytics failure cannot fail an
MCP call. The daily report uses sampling-aware aggregate queries and degrades to a
clearly labeled missing section if the dataset cannot be read.

A separate SQLite-backed Durable Object keeps lifetime counters for aggregate MCP
events: initializations, tool calls, completed results, changed messages, warnings,
failures, and capacity rejects. It stores no request content or stable identity. A
report-only bearer secret protects the read endpoint; the editor signing secret is
never reused. Because MCP provides no stable installation identifier, the service
does not claim that an initialization count is a unique-install count.

## Online-learning isolation

Reflection evidence, local detector rules, recurring rewrite preferences, logs, and
named scoring profiles live under
`$ZERO_SLOP_HOME` (default `~/.zero-slop`) with owner-only file permissions. They are
not committed and are not overwritten by skill updates. The scorer loads the reviewed
shared taxonomy first, then this private overlay on every run.

One edit cannot activate a pattern. Phrase evidence needs the same cut across three
content-distinct before/after pairs; single words need five. Candidate rules must also
be new and must not match or borrow four consecutive words from the certified human
corpus. Repeated kept-text evidence can lower a local weight. Reconfirmation keeps a
local rule current; stale local detector rules decay after 18 months. A rewrite
preference also needs the same replacement across three content-distinct pairs and is
retired after 18 months without confirmation.

These controls limit blast radius; they do not make feedback trustworthy in the
cryptographic sense. A determined local user controls their own overlay. Shared changes
still require an explicit export, review, re-gating, tests, version bump, and release.

## File integrity and path safety

Learning uses process-safe lock directories plus same-directory atomic replacement, so
concurrent reflections cannot silently overwrite one another and a crash cannot leave
half-written JSON. Corrupt reflection state fails closed instead of being reset.
Malformed learned rules degrade to the last valid shared layer rather than crashing the
scorer.

Voice-profile names are restricted to a short filename-safe alphabet. Contribution
exports must remain inside the working directory, cannot target `data/`, and cannot
overwrite an existing file. Imported contributions are untrusted: Zero Slop discards
their regexes, rebuilds patterns locally from the reviewed spans, and reruns the safety
gate.

The npm installer stages a complete copy before replacement. `--force` refuses roots,
the home directory, the current project, symlinks, files, and nonempty directories that
do not contain a verifiable Zero Slop runtime. A failed copy leaves the installed skill
in place.

## Known limits

- A sample-based `--voice` profile records an existing lexicon or context-gated
  watchlist term after one exact word match. It must be selected explicitly and
  does not learn cadence, syntax, humor, tone, arbitrary phrases, or the writer's
  full style.
- The human safety corpus contains twelve prose samples. It is a regression floor, not
  proof that a pattern is safe for every dialect, genre, or language.
- The 0–100 result is a transparent heuristic surface score, not a calibrated
  probability that AI wrote the text.
- Scripted fidelity checks cover figures, names, quotations, links, asserted
  feelings, and protected document structure. Claim meaning, qualifiers, and voice
  still require the final semantic review described in `SKILL.md`.
- Feedback recurrence proves content diversity, not independent authorship. Local
  isolation prevents that limitation from changing the shared detector automatically.

## Reporting

Open a GitHub issue, or use the email address on the maintainer's GitHub profile for a
report you would rather not file publicly.
