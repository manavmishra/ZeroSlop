#!/usr/bin/env python3
"""Repair stale release surfaces using existing publishers; never change versions."""
import json
import subprocess
import urllib.error

from deploy_mcp import API, MCP, VERSION, SHA, fetch_json
from publication_guard import publication_guard
from npm_record import publication_state


def missing_json(url, *, read=fetch_json):
    try:
        return read(url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {}
        raise


def repair_plan(version, sha, *, read=fetch_json):
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("a stable release version is required")
    tag = f"v{version}"
    plan = []
    npm = publication_state(version, sha, fetch_fn=read)
    if npm["status"] == "unpublished":
        plan.append(("publish-npm.yml", tag, []))
    release = missing_json(f"{API}/releases/latest", read=read)
    assets = {asset.get("name") for asset in release.get("assets", [])
              if asset.get("state") == "uploaded" and isinstance(asset.get("size"), int) and asset["size"] > 0}
    if (release.get("tag_name") != tag or release.get("draft") is not False
            or not {"zero-slop.zip", "zero-slop-single-file.md", "Zero-Slop-One-Pager.pdf"} <= assets):
        plan.append(("release-on-tag.yml", tag, []))
    else:
        try:
            health = read(f"{MCP}/health")
        except urllib.error.HTTPError as exc:
            # Only the gateway's recognizable readiness response permits a
            # repair. An unknown proxy outage does not justify a blind deploy.
            if exc.code != 503:
                raise
            body = exc.read(262145)
            if len(body) > 262144:
                raise ValueError("health metadata exceeds its size bound")
            health = json.loads(body)
            if health.get("service") != "zero-slop-mcp":
                raise ValueError("unrecognized health failure; refusing a blind redeploy")
        card = read(f"{MCP}/.well-known/mcp/server-card.json")
        spec = read(f"{MCP}/openapi.json")
        if (health.get("ok") is not True or health.get("editorConfigured") is not True
                or health.get("scorer", {}).get("ok") is not True
                or health.get("version") != version or health.get("scorer", {}).get("scorerVersion") != version
                or card.get("serverInfo", {}).get("version") != version or spec.get("info", {}).get("version") != version):
            plan.append(("deploy-mcp.yml", "main", ["-f", f"release_tag={tag}"]))
    registry = missing_json("https://registry.modelcontextprotocol.io/v0.1/servers/io.github.manavmishra%2Fzero-slop/versions/latest", read=read)
    official = registry.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
    if (registry.get("server", {}).get("version") != version
            or official.get("status") != "active" or official.get("isLatest") is not True):
        plan.append(("publish-mcp.yml", tag, []))
    return plan


def main():
    package = json.loads(open("package.json").read())
    version = package["version"]
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("package version is invalid")
    tag = f"v{version}"
    reference = missing_json(f"{API}/git/ref/tags/{tag}")
    if not reference:
        # sync-release independently verifies all three validation jobs before
        # creating anything, including on this manual recovery path.
        subprocess.run(["gh", "workflow", "run", "sync-release.yml", "--ref", "main"], check=True)
        print("Requested validated release recovery; no version or tag was changed here.")
        return
    obj = reference.get("object", {})
    for _ in range(5):
        if not isinstance(obj.get("sha"), str) or not SHA.fullmatch(obj["sha"]):
            raise ValueError("invalid tag object")
        if obj.get("type") == "commit":
            break
        if obj.get("type") != "tag":
            raise ValueError("invalid release tag")
        obj = fetch_json(f"{API}/git/tags/{obj['sha']}").get("object", {})
    result = publication_guard(tag, obj.get("sha"))
    for workflow, ref, inputs in repair_plan(result["version"], result["sha"]):
        runs = fetch_json(f"{API}/actions/workflows/{workflow}/runs?per_page=20").get("workflow_runs", [])
        if any(run.get("status") in ("queued", "in_progress", "waiting", "pending")
               and (run.get("head_sha") == result["sha"] or workflow == "deploy-mcp.yml") for run in runs):
            print(f"{workflow}: repair already running")
            continue
        subprocess.run(["gh", "workflow", "run", workflow, "--ref", ref, *inputs], check=True)
        print(f"{workflow}: requested repair for {tag}")
    print("Website and Homebrew reconcile in their own repositories without cross-repository secrets.")


if __name__ == "__main__":
    main()
