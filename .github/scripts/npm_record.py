#!/usr/bin/env python3
"""Read-only npm publication decision; never publish or change a dist-tag."""
import argparse
import json
import sys
import urllib.error
from pathlib import Path

from deploy_mcp import SHA, VERSION, fetch_json

NPM = "https://registry.npmjs.org/zero-slop"


def publication_state(version, sha, *, fetch_fn=fetch_json):
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("a stable release version is required")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("the full validated checkout SHA is required")
    try:
        exact = fetch_fn(f"{NPM}/{version}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"status": "unpublished", "version": version}
        raise
    if (not isinstance(exact, dict) or exact.get("name") != "zero-slop"
            or exact.get("version") != version or exact.get("gitHead") != sha):
        raise ValueError(
            f"npm zero-slop@{version} exists but does not match the validated checkout SHA; "
            "inspect the published record before taking further action"
        )
    latest_missing = False
    try:
        latest = fetch_fn(f"{NPM}/latest")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        latest, latest_missing = None, True
    if not latest_missing and (not isinstance(latest, dict) or latest.get("name") != "zero-slop"
                               or not isinstance(latest.get("version"), str)
                               or not VERSION.fullmatch(latest["version"])):
        raise ValueError("npm latest metadata is invalid; publication is blocked")
    if latest_missing or latest["version"] != version:
        raise ValueError(
            f"npm latest promotion requires maintainer auth: zero-slop@{version} is already published "
            "from the validated checkout, but latest points elsewhere or is missing. "
            "A maintainer must verify the intended release and update the npm latest dist-tag; "
            "this workflow will not attempt a dist-tag write."
        )
    if latest.get("gitHead") != sha:
        raise ValueError("npm latest does not match the validated checkout SHA; publication is blocked")
    return {"status": "current", "version": version}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--github-output")
    args = parser.parse_args(argv)
    try:
        result = publication_state(args.version, args.sha)
        if args.github_output:
            # Fixed keys and validated version only; no registry data becomes
            # workflow syntax. Output is written only after every check succeeds.
            with Path(args.github_output).open("a") as output:
                output.write(f"already={'true' if result['status'] == 'current' else 'false'}\n")
                output.write(f"version={args.version}\n")
        print(json.dumps(result))
        return 0
    except Exception as exc:
        print(f"NPM_PUBLICATION_BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
