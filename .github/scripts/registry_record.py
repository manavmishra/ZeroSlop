#!/usr/bin/env python3
"""Check an immutable official MCP Registry record before an idempotent publish."""
import argparse
import json
import sys
import urllib.error
from pathlib import Path

from deploy_mcp import VERSION, fetch_json

BASE = "https://registry.modelcontextprotocol.io/v0.1/servers/io.github.manavmishra%2Fzero-slop/versions/"


def published_record(server, *, fetch_fn=fetch_json):
    version = server.get("version")
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("server.json must name a stable version")
    try:
        result = fetch_fn(BASE + version)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise
    record = result.get("server", {})
    official = result.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
    if (record.get("name") != server.get("name") or record.get("version") != version
            or record.get("remotes") != server.get("remotes") or official.get("status") != "active"):
        raise ValueError("the existing immutable MCP record differs from the released server; do not overwrite it")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github-output")
    args = parser.parse_args()
    try:
        published = published_record(json.loads(Path("server.json").read_text()))
        line = f"published={str(published).lower()}\n"
        if args.github_output:
            with Path(args.github_output).open("a") as output:
                output.write(line)
        print(line, end="")
        return 0
    except Exception as exc:
        print(f"REGISTRY_CHECK_FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
