#!/usr/bin/env python3
"""Read-only release identity and live-runtime gates for MCP deployment CI."""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.github.com/repos/manavmishra/ZeroSlop"
RAW = "https://raw.githubusercontent.com/manavmishra/ZeroSlop"
MCP = "https://mcp.zero-slop.ai"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


def fetch_json(url):
    headers = {"User-Agent": "zero-slop-mcp-deployment"}
    token = os.environ.get("GH_TOKEN")
    if token and url.startswith(API + "/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read(262145)
    if len(body) > 262144:
        raise ValueError("metadata exceeds 256 KiB")
    return json.loads(body)


def _version(package):
    version = package.get("version") if isinstance(package, dict) else None
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("missing or invalid release version")
    return version


def release_guard(tag, *, expected_sha=None, fetch_fn=fetch_json):
    if not isinstance(tag, str) or not tag.startswith("v") or not VERSION.fullmatch(tag[1:]):
        raise ValueError("release_tag must be an existing stable vX.Y.Z release tag")
    if expected_sha is not None and not SHA.fullmatch(expected_sha):
        raise ValueError("expected SHA must be a full commit hash")
    release = fetch_fn(f"{API}/releases/latest")
    if (not isinstance(release, dict) or release.get("draft") is not False
            or release.get("prerelease") is not False
            or not isinstance(release.get("tag_name"), str)
            or not release["tag_name"].startswith("v")
            or not VERSION.fullmatch(release["tag_name"][1:])):
        raise ValueError("latest release metadata is invalid or not a stable published release")
    if release["tag_name"] != tag:
        return {"status": "superseded"}
    reference = fetch_fn(f"{API}/git/ref/tags/{tag}")
    if not isinstance(reference, dict) or reference.get("ref") != f"refs/tags/{tag}":
        raise ValueError("tag reference does not identify the requested release")
    obj = reference.get("object")
    for _ in range(5):
        if (not isinstance(obj, dict) or not isinstance(obj.get("sha"), str)
                or not SHA.fullmatch(obj["sha"])):
            raise ValueError("tag reference has no valid immutable SHA")
        if obj.get("type") == "commit":
            break
        if obj.get("type") != "tag":
            raise ValueError("release tag does not resolve to a commit")
        annotated = fetch_fn(f"{API}/git/tags/{obj['sha']}")
        obj = annotated.get("object") if isinstance(annotated, dict) else None
    else:
        raise ValueError("too many nested annotated tags")
    sha = obj["sha"]
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("release tag moved after its immutable commit was selected")
    version = _version(fetch_fn(f"{RAW}/{sha}/package.json"))
    if tag != f"v{version}":
        raise ValueError("tag and packaged release version disagree")
    if _version(fetch_fn(f"{RAW}/main/package.json")) != version:
        return {"status": "superseded"}
    return {"status": "current", "sha": sha, "version": version}


def validate_runtime(version, health, card):
    scorer = health.get("scorer") if isinstance(health, dict) else None
    if (not isinstance(scorer, dict) or health.get("service") != "zero-slop-mcp"
            or health.get("ok") is not True or scorer.get("ok") is not True
            or health.get("editorConfigured") is not True):
        raise ValueError("MCP gateway/scorer readiness is missing or degraded")
    if health.get("version") != version or scorer.get("scorerVersion") != version:
        raise ValueError("MCP gateway/scorer version has not converged")
    info = card.get("serverInfo") if isinstance(card, dict) else None
    if not isinstance(info, dict) or info.get("name") != "zero-slop" or info.get("version") != version:
        raise ValueError("MCP server-card has not converged")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    guard = commands.add_parser("guard")
    guard.add_argument("--tag", required=True)
    guard.add_argument("--expected-sha")
    guard.add_argument("--github-output")
    health = commands.add_parser("health")
    health.add_argument("--version", required=True)
    health.add_argument("--wait-seconds", type=int, default=90)
    args = parser.parse_args(argv)
    try:
        if args.command == "guard":
            result = release_guard(args.tag, expected_sha=args.expected_sha)
            if args.github_output:
                with Path(args.github_output).open("a") as output:
                    output.write("".join(f"{key}={value}\n" for key, value in result.items()))
            print(json.dumps(result))
            return 0
        if not VERSION.fullmatch(args.version) or not 0 <= args.wait_seconds <= 120:
            raise ValueError("health requires a stable version and a wait between 0 and 120 seconds")
        deadline = time.monotonic() + args.wait_seconds
        while True:
            try:
                validate_runtime(args.version, fetch_json(f"{MCP}/health"),
                                 fetch_json(f"{MCP}/.well-known/mcp/server-card.json"))
                print(f"MCP_DEPLOYED: gateway, scorer and server-card are healthy at {args.version}")
                return 0
            except Exception as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"MCP runtime did not converge: {exc}") from exc
                print(f"MCP_PROPAGATING: {exc}")
                time.sleep(min(5, max(0, deadline - time.monotonic())))
    except Exception as exc:
        print(f"MCP_GATE_FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
