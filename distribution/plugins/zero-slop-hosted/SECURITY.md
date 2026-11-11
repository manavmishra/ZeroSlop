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
it. Cloudflare Workers AI handles hosted editing first. If it cannot return a usable
edit, Zero Slop may send the draft and editing inputs through OpenRouter to a free
model provider that may keep the draft and the edit or use them to train models. Zero Slop
does not keep drafts or rewrites or activate private learning through this connector.
See https://zero-slop.ai/privacy/ for provider handling and separate retention policies
for infrastructure and usage records.

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
