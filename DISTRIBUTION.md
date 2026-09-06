# Install Zero Slop anywhere

Zero Slop ships one writing workflow through several standard package formats.
The skill uses the AI assistant you already have. The hosted MCP connector is
the no-install option for clients that support Streamable HTTP.

## Direct install and connection

| Platform | Install or connect |
|---|---|
| Agent Skills clients | `npx skills add manavmishra/ZeroSlop --global` |
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
plugin and extension manifest, the npm package, GitHub release assets, and the
MCP Registry record. A version tag publishes npm, rebuilds the GitHub release,
and updates the official MCP Registry. The website pulls the released skill,
checks browser-to-skill parity, deploys the exact build that passed, and checks
the live `/try/` manifest after deployment.

The website also reconciles with the skill repository every hour. Immediate
cross-repository dispatch can be enabled with a fine-grained GitHub token named
`WEBSITE_SYNC_TOKEN`; it needs Actions write access only to
`manavmishra/ZSWebpage`.

## Maintainer release check

```sh
python3 scripts/check_distribution_manifests.py
python3 scripts/check_release_surfaces.py --require-network --wait-seconds 600
```

These checks report drift. They do not rewrite published records silently.
