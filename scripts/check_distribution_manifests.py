#!/usr/bin/env python3
"""Validate every public plugin, extension, and MCP manifest without network I/O."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
MCP_URL = "https://mcp.zero-slop.ai/mcp"


def load(relative: str) -> dict:
    path = ROOT / relative
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{relative} must contain a JSON object")
    return value


def require(condition: bool, message: str, problems: list[str]) -> None:
    if not condition:
        problems.append(message)


def main() -> int:
    problems: list[str] = []
    package = load("package.json")
    version = package.get("version")
    require(isinstance(version, str) and VERSION_RE.fullmatch(version) is not None,
            "package.json has no semantic version", problems)

    manifests = {
        "Claude plugin": load(".claude-plugin/plugin.json"),
        "Codex plugin": load(".codex-plugin/plugin.json"),
        "Agent Plugin": load("plugin.json"),
        "Gemini extension": load("gemini-extension.json"),
        "MCP Registry": load("server.json"),
    }
    for name, manifest in manifests.items():
        require(manifest.get("version") == version,
                f"{name} says {manifest.get('version')!r}, package.json says {version!r}", problems)

    agent = manifests["Agent Plugin"]
    require(agent.get("$schema") == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "plugin.json uses the wrong schema", problems)
    require(agent.get("name") == "zero-slop", "plugin.json uses the wrong name", problems)
    require(set(agent) <= {"$schema", "name", "version", "description", "author", "homepage",
                            "repository", "license", "keywords", "extensions"},
            "plugin.json contains fields outside Agent Plugins 1.0.0", problems)

    portable_mcp = load("mcp.json")
    require(portable_mcp.get("$schema") == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcp.json uses the wrong schema", problems)
    require(portable_mcp.get("mcpServers", {}).get("zero-slop") == {
        "type": "streamable-http", "url": MCP_URL,
    }, "mcp.json does not point at the public Streamable HTTP server", problems)

    claude_mcp = load(".mcp.json")
    require(claude_mcp.get("mcpServers", {}).get("zero-slop") == {
        "type": "http", "url": MCP_URL,
    }, ".mcp.json does not point at the public HTTP server", problems)

    gemini = manifests["Gemini extension"]
    gemini_server = gemini.get("mcpServers", {}).get("zero-slop", {})
    require(gemini_server.get("httpUrl") == MCP_URL,
            "gemini-extension.json does not point at the public HTTP server", problems)
    require(gemini_server.get("includeTools") == ["deslop"],
            "Gemini extension must expose only the deslop tool", problems)
    require(gemini_server.get("timeout") == 45_000,
            "Gemini extension must use the bounded 45-second timeout", problems)

    registry = manifests["MCP Registry"]
    require(registry.get("remotes") == [{"type": "streamable-http", "url": MCP_URL}],
            "server.json does not advertise the public Streamable HTTP server", problems)
    require(registry.get("name") == "io.github.manavmishra/zero-slop",
            "server.json uses the wrong registry name", problems)

    require(manifests["Claude plugin"].get("mcpServers") == "./.mcp.json",
            "Claude plugin does not bundle the MCP connector", problems)
    require(manifests["Codex plugin"].get("mcpServers") == "./mcp.json",
            "Codex plugin does not bundle the MCP connector", problems)

    skill = (ROOT / "SKILL.md").read_text()
    match = re.search(r'^\s*version:\s*"([0-9.]+)"\s*$', skill, re.MULTILINE)
    require(match is not None and match.group(1) == version,
            "SKILL.md and package.json versions differ", problems)

    package_lock = load("package-lock.json")
    require(package_lock.get("version") == version,
            "package-lock.json and package.json versions differ", problems)
    require(package_lock.get("packages", {}).get("", {}).get("version") == version,
            "package-lock.json root package has the wrong version", problems)

    text_surfaces = {
        "README badge": ("README.md", f"version-{version}-72528F"),
        "one-pager": ("ONE-PAGER.md", f"v{version}"),
        "plugin mirror": ("skills/zero-slop/SKILL.md", f'version: "{version}"'),
        "single-file bundle": ("dist/zero-slop-single-file.md", f'version: "{version}"'),
        "website source snapshot": ("website/app/page.tsx", f'skillVersion = "{version}"'),
        "website machine summary": ("website/public/llms.txt", f"Current version: {version}"),
        "website full machine summary": ("website/public/llms-full.txt", f"Current version: {version}"),
        "gateway configuration": ("mcp/gateway/wrangler.jsonc", f'"SCORER_VERSION": "{version}"'),
        "scorer Worker manifest": ("mcp/scorer/src/scorer-manifest.json", f'"version": "{version}"'),
    }
    for name, (relative, expected) in text_surfaces.items():
        require(expected in (ROOT / relative).read_text(),
                f"{name} does not advertise {version}", problems)

    if problems:
        for problem in problems:
            print(f"distribution manifest error: {problem}")
        return 1
    print(f"All plugin, extension, and MCP manifests agree on Zero Slop {version}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
