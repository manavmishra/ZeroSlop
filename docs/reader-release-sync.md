# 2.12.0 distribution synchronization

Local verification: September 10, 2026 Pacific / September 11 UTC.
`package.json` is the version authority. This is an unpublished candidate;
changing a manifest is not evidence of registry publication or deployment.

| Surface | How it gets the version | Candidate state |
| --- | --- | --- |
| npm and Node CLI | `package.json`; installed CLI reads its package version | 2.12.0; clean offline package installation verified |
| Claude, Codex, Cursor-compatible plugin, Gemini | Distribution manifests and generated `skills/zero-slop/` mirror | 2.12.0; mirror and manifest checks passed |
| MCP Registry submission | `server.json`, released from the matching validated tag | 2.12.0 locally; publication not performed |
| MCP server and REST/OpenAPI | Gateway `SCORER_VERSION`; MCP initialization, health and OpenAPI use that value | 2.12.0 configuration; not deployed |
| Hosted scorer | Generated scorer manifest and byte-pinned Python/data payload | 2.12.0; no scoring-code change from 2.11.6 |
| Skill ZIP and single-file bundle | Generated from canonical skill and runtime references | 2.12.0; current, deterministic ZIP with exactly one `SKILL.md` |
| PyPI/uv scorer distribution | `pyproject.toml` and generated Python package version | 2.12.0 locally; remains the offline scorer/gate package, not the full agent skill |
| Homebrew | Formula builder reads `package.json` and verifies the published npm tarball integrity | Targets 2.12.0; formula publication waits for npm, not a placeholder checksum |
| Website, `/try/`, browser scorer and site ZIP link | Production website imports one immutable, published release after npm and healthy gateway/scorer agree | Intentionally remains on its last verified release until 2.12.0 is published |

## Version alignment is not feature equivalence

The new reader workflow is an **optional host-agent skill workflow**. Its helper
prepares source-bound packets and renders supplied journals; it does not run a
model. npm-installed skills, the plugin mirror and ZIP include its instructions
and helper. The single-file bundle includes the instructions.

REST, remote MCP, `zero-slop deslop`, and `/try/` retain their existing editing
contract. They do not run the new multi-reader review or expose a reader-review
endpoint in this candidate. PyPI remains a scorer/gate distribution. A shared
2.12.0 version must not be presented as reader-review feature parity across these
different interfaces.

## Checks run

- Distribution manifests, plugin mirror, single-file bundle, ZIP and PyPI mirror
  checks pass at 2.12.0; `zero-slop --version` returns 2.12.0.
- 69 Python release-surface, distribution and release-automation tests pass.
  These include wrong-version and tampered-package failures for public-surface
  validation; mocked services do not establish live deployment.
- Eight Homebrew formula tests pass: missing release, wrong version/package,
  unexpected tarball host, absent integrity and tampered bytes are rejected.
- Fifteen production-website release-source tests pass: unpublished releases,
  missing downloads and mismatched/unhealthy runtimes cannot replace the pin.
- Clean npm-package acceptance runs offline on macOS ARM64 with Node 24.19.0,
  installs only into a temporary directory, exercises the CLI and scorer, and
  verifies the new reader files survive package and agent-skill installation.

## Release order

1. Authorize and commit the reviewed candidate; complete required CI on `main`.
2. Publish the matching npm/PyPI packages, immutable GitHub tag/assets and MCP
   Registry submission through the existing workflows. Verify actual receipts.
3. Deploy the matching hosted scorer and gateway; verify health, MCP
   initialization and `/openapi.json` all name 2.12.0.
4. Import that verified release into `manavmishra/ZSWebpage`; build and test the
   vendored scorer, `/try/`, displayed version and ZIP target together. Deploy
   only from that repository. Preserve the snapshot's refusal guard.
5. Generate and test the Homebrew formula from the published npm bytes; verify
   its version and checksum. Run the full public release-surface audit, including
   website, downloaded ZIP, npm, MCP Registry and Homebrew, after convergence.

The existing release/sync workflows implement this gating and have hourly
reconciliation paths. This is eventual convergence, not an atomic cross-service
release. Failed readiness checks keep the website on the last verified version.
No publication, deployment, global skill installation or billing change was
performed during this verification pass.
