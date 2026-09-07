#!/usr/bin/env python3
"""Require a new semantic version when a released runtime changes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

from build_plugin import EXCLUDE as PLUGIN_EXCLUDE, ITEMS as PLUGIN_ITEMS


ROOT = Path(__file__).resolve().parent.parent
EXACT_RELEASE_PATHS = {
    ".mcp.json",
    "SKILL.md",
    "gemini-extension.json",
    "mcp.json",
    "package.json",
    "plugin.json",
    "server.json",
}
RELEASE_PREFIXES = (
    ".claude-plugin/",
    ".codex-plugin/",
    "bin/",
    "data/",
    "mcp/",
    "references/",
    "scripts/",
)


def is_release_path(path: str) -> bool:
    parsed = PurePosixPath(path)
    normalized = parsed.as_posix()
    # Match the packaged skill's exclusions, without applying them to MCP code
    # or distribution manifests outside that mirror. New runtime files still
    # require a bump unless packaging explicitly excludes them.
    if (parsed.parts and parsed.parts[0] in PLUGIN_ITEMS
            and any(part in PLUGIN_EXCLUDE for part in parsed.parts[1:])):
        return False
    return normalized in EXACT_RELEASE_PATHS or normalized.startswith(RELEASE_PREFIXES)


def version_at(ref: str) -> str:
    raw = subprocess.check_output(
        ["git", "show", f"{ref}:package.json"], cwd=ROOT, text=True
    )
    return str(json.loads(raw)["version"])


def changed_paths(base: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base}...HEAD"], cwd=ROOT, text=True
    )
    return [line for line in output.splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="commit or ref to compare with HEAD")
    args = parser.parse_args(argv)

    previous = version_at(args.base)
    current = str(json.loads((ROOT / "package.json").read_text())["version"])
    released = [path for path in changed_paths(args.base) if is_release_path(path)]
    if released and current == previous:
        print("A released runtime changed without a version bump:", file=sys.stderr)
        for path in released:
            print(f"  {path}", file=sys.stderr)
        print(f"package.json is still {current}", file=sys.stderr)
        return 1
    if current != previous and not released:
        print(f"Version changed from {previous} to {current}, but no release file changed.")
    else:
        print(f"Release version check passed ({previous} -> {current}; {len(released)} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
