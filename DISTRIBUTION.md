# Install Zero Slop anywhere

Zero Slop ships one writing workflow through several standard package formats.
The skill uses the AI assistant you already have. The hosted MCP connector is
the no-install option for clients that support Streamable HTTP.

## Direct install and connection

| Platform | Install or connect |
|---|---|
| Agent Skills clients | `npx skills add manavmishra/ZeroSlop --global` |
| PyPI | `pip install zero-slop` |
| GitHub Actions | `uses: manavmishra/ZeroSlop@v2.10.2` |
| pre-commit | `repo: https://github.com/manavmishra/ZeroSlop`, hook `zero-slop` |
| npm | `npx zero-slop install` |
| Claude Code and Cowork | `/plugin marketplace add manavmishra/ZeroSlop`, then `/plugin install zero-slop@zero-slop` |
| Gemini CLI | `gemini extensions install https://github.com/manavmishra/ZeroSlop --auto-update` |
| Codex | `codex mcp add zero-slop --url https://mcp.zero-slop.ai/mcp` |
| Claude Code MCP | `claude mcp add --transport http zero-slop --scope user https://mcp.zero-slop.ai/mcp` |
| ChatGPT, Claude.ai, Grok, Cursor, Gemini, and other MCP clients | Add `https://mcp.zero-slop.ai/mcp` as a custom connector where remote MCP servers are supported |

The canonical MCP entry is `io.github.manavmishra/zero-slop` in the official
Model Context Protocol Registry. Other MCP catalogs can import that record
without introducing a second package or server.

## Directory packages

The repository contains the files each major directory expects:

| Directory | Package in this repository | Publication route |
|---|---|---|
| OpenAI Plugins Directory | Codex plugin, Agent Skill, and hosted MCP | OpenAI Platform submission review |
| Anthropic Plugin Directory | `.claude-plugin/plugin.json`, `skills/`, and `.mcp.json` | Claude or Console plugin submission review |
| Anthropic Connectors Directory | Hosted MCP, public docs, privacy policy, and tool annotations | Connectors Directory review |
| Gemini CLI extension gallery | `gemini-extension.json`, `skills/`, and hosted MCP | Automatic crawl of tagged repositories with the `gemini-cli-extension` topic |
| Cursor Marketplace | `plugin.json`, `skills/`, and `mcp.json` | Cursor Marketplace review |
| Grok | Hosted MCP | Available as a custom connector; xAI does not document a public catalog-submission form |

Directory review is separate from technical readiness. A listing is not called
published until the directory accepts it and provides a public URL. The website
shows only accepted listings with public URLs.

## One release number

`package.json` is the release version. CI checks it against `SKILL.md`, every
plugin and extension manifest, and the hosted runtime configuration. Set the
version there, then run `node distribution/sync-version.mjs` to update the
release labels. This maintainer command leaves historical benchmark results alone;
rerun version-bound evaluations before publication.

All three validation jobs must pass at the exact commit before an immutable tag
can publish npm, the GitHub downloads or the official MCP Registry record. The
private scorer and the shared REST/MCP gateway deploy from that tag. OpenAPI's
product version comes from the gateway configuration; the `/v1/` route identifies
the API contract, not the current package version.

The website imports a published release only after its downloads, npm package
and hosted scorer are ready. It verifies the vendored files and browser parity
before deployment. Download buttons point to that release's ZIP and single-file
skill, so an older page cannot silently offer a newer runtime.

Three hourly reconciliation jobs check the canonical release, website and
Homebrew tap. The tap derives its formula from the release's integrity-checked
npm tarball, then audits, installs and tests it before committing. The canonical
audit checks npm package bytes, skill ZIP contents, browser files, OpenAPI,
hosted versions, the MCP Registry record and the tap checksum. Failed checks
remain visible in Actions; unknown network failures never count as a pass.

These services publish independently. Brief propagation gaps and delayed
schedules are possible; synchronization is verified after publication, not
assumed to be instantaneous. Existing pinned installations stay pinned until
their owners update them. Marketplace approval and third-party crawl schedules
are outside this release process.

Optional immediate website dispatch uses `WEBSITE_SYNC_TOKEN`, a fine-grained
token scoped to Contents write on `manavmishra/ZSWebpage` for GitHub's
repository-dispatch endpoint. The scheduled sync works without that token.

## Maintainer release check

```sh
python3 scripts/check_distribution_manifests.py
python3 scripts/check_release_surfaces.py --require-network --wait-seconds 600
```

The scripts above only report drift. The scheduled recovery workflow can rerun
the existing publishers for the validated release; it does not invent a version,
move a tag or upgrade a user's installed copy.
