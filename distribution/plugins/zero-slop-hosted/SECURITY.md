# Hosted plugin security

## Scope and supported versions

This package contains a static manifest, documentation, an icon, and one anonymous
HTTPS MCP connection to `https://mcp.zero-slop.ai/mcp`. It contains no local skill,
executable code, dependency installer, credentials, or hooks. This directory is a
review candidate; its presence does not establish publication or deployment.
Supported published versions are identified in the repository's release notes:
https://github.com/manavmishra/ZeroSlop/releases.

## Remote processing and limits

The declared server receives the draft, genre, and optional audience supplied to
it. Hosted processing uses Cloudflare and, when configured, a bounded OpenRouter
fallback with eligible zero-data-retention providers. Zero Slop does not persist
drafts or rewrites or activate private learning through this connector. Operational
counters and infrastructure processing have separate retention policies described
at https://zero-slop.ai/privacy/.

Capacity limits or unavailable providers can prevent an edit. Writing scores are
heuristics, not AI-authorship probabilities; source checks are not a guarantee of
factual accuracy. Review returned edits before publishing. A marketplace scan or
listing is not security, privacy, data-quality, or compliance certification.

## Reporting a vulnerability

Send suspected vulnerabilities privately to `manav@prompeteer.com`. Include the
affected published version or source commit, the relevant component, and a minimal
synthetic reproduction. Do not send credentials, private drafts, or personal data.
Avoid posting exploit details in a public issue before the maintainer has reviewed
the report. Ordinary non-sensitive support requests belong at
https://github.com/manavmishra/ZeroSlop/issues.
