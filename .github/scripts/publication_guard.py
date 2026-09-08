#!/usr/bin/env python3
"""Admit only an immutable, validated release from trusted main. No writes."""
import argparse
import json
import sys

from deploy_mcp import API, RAW, SHA, VERSION, fetch_json


def validated_main(sha, *, fetch_fn=fetch_json):
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("a full validated commit SHA is required")
    comparison = fetch_fn(f"{API}/compare/{sha}...main")
    if comparison.get("status") not in ("ahead", "identical"):
        raise ValueError("release commit does not belong to trusted main")
    runs = fetch_fn(f"{API}/actions/workflows/validate.yml/runs?event=push&branch=main&head_sha={sha}&per_page=10")
    matching = [run for run in runs.get("workflow_runs", [])
                if run.get("head_sha") == sha and run.get("head_branch") == "main"
                and run.get("event") == "push"]
    if not matching:
        raise ValueError("no trusted main validation run exists for this commit")
    # A failed rerun must not be hidden by an older successful attempt.
    run = max(matching, key=lambda item: (item.get("run_number", 0), item.get("run_attempt", 0)))
    run_id = run.get("id")
    if not isinstance(run_id, int):
        raise ValueError("validation run has no numeric identity")
    jobs = fetch_fn(f"{API}/actions/runs/{run_id}/jobs?filter=latest&per_page=100")
    required = {"validate", "website", "mcp"}
    passed = {job.get("name") for job in jobs.get("jobs", [])
              if job.get("status") == "completed" and job.get("conclusion") == "success"}
    if not required <= passed:
        raise ValueError("release requires successful code, website and MCP validation at the exact commit")


def publication_guard(tag, sha, *, require_tag=True, fetch_fn=fetch_json):
    if not isinstance(tag, str) or not tag.startswith("v") or not VERSION.fullmatch(tag[1:]):
        raise ValueError("publication requires a stable vX.Y.Z tag")
    validated_main(sha, fetch_fn=fetch_fn)
    package = fetch_fn(f"{RAW}/{sha}/package.json")
    current = fetch_fn(f"{RAW}/main/package.json")
    if package.get("name") != "zero-slop" or package.get("version") != tag[1:]:
        raise ValueError("tag does not match the validated package version")
    if current.get("version") != tag[1:]:
        raise ValueError("a newer source version superseded this release")
    if require_tag:
        reference = fetch_fn(f"{API}/git/ref/tags/{tag}")
        if reference.get("ref") != f"refs/tags/{tag}":
            raise ValueError("tag reference does not match the requested release")
        obj = reference.get("object", {})
        for _ in range(5):
            if not isinstance(obj.get("sha"), str) or not SHA.fullmatch(obj["sha"]):
                raise ValueError("invalid tag object")
            if obj.get("type") == "commit":
                break
            if obj.get("type") != "tag":
                raise ValueError("tag must resolve to a commit")
            obj = fetch_fn(f"{API}/git/tags/{obj['sha']}").get("object", {})
        else:
            raise ValueError("too many nested tags")
        if obj["sha"] != sha:
            raise ValueError("the immutable tag does not identify this checkout")
    return {"version": tag[1:], "sha": sha, "tag": tag}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--before-tag", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(publication_guard(args.tag, args.sha, require_tag=not args.before_tag)))
        return 0
    except Exception as exc:
        print(f"PUBLICATION_BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
