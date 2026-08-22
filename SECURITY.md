# Security posture

## Runtime boundary

The installed skill ships seven standard-library Python modules:

| File | Purpose | Writes | Network |
|---|---|---|---|
| `scripts/slopscore.py` | score, heatmap, and fidelity checks | none | none |
| `scripts/predictability.py` | create and score deterministic cloze probes | none | none |
| `scripts/rerank.py` | rank candidate rewrites | optional user-selected output | none |
| `scripts/learn.py` | private online learning, voice profiles, reviewed imports/exports | `$ZERO_SLOP_HOME`; shared taxonomy only through explicit maintainer `--merge --apply` | none |
| `scripts/calibrate.py` | corpus calibration and shared-pattern maintenance | explicit calibration output or shared learned data | none |
| `scripts/safeio.py` | locks and atomic file replacement | only on behalf of the two writers above | none |
| `scripts/version_check.py` | optional release check | none | one metadata-only GitHub API request |

Scoring and rewriting do not transmit the draft. The version checker sends only a GET
for the latest public release tag, times out after 2.5 seconds, fails open, and can be
disabled with `ZS_NO_UPDATE_CHECK=1`.

Build, packaging, benchmark, chart, PDF, website, and test utilities remain in the
repository but are excluded from the installed plugin runtime.

## Online-learning isolation

Reflection evidence, local detector rules, recurring rewrite preferences, logs, and
voice profiles live under
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

## Known limits

- The human safety corpus contains twelve prose samples. It is a regression floor, not
  proof that a pattern is safe for every dialect, genre, or language.
- The 0–100 result is a transparent heuristic surface score, not a calibrated
  probability that AI wrote the text.
- Scripted fidelity checks cover figures, names, quotations, links, and asserted
  feelings. Claim meaning, qualifiers, voice, and format still require the final
  semantic review described in `SKILL.md`.
- Feedback recurrence proves content diversity, not independent authorship. Local
  isolation prevents that limitation from changing the shared detector automatically.

## Reporting

Open a GitHub issue, or use the email address on the maintainer's GitHub profile for a
report you would rather not file publicly.
