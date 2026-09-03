#!/usr/bin/env python3
"""Confirm that GitHub and npm serve the version in this repository.

The check distinguishes an unreachable service from a reachable service with a
missing or stale artifact. Offline developer runs may skip unreachable hosts;
release automation uses ``--require-network`` and a bounded wait so publication
latency cannot be mistaken for either success or permanent drift.
"""
import argparse
import io
import json
import re
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "manavmishra/ZeroSlop"
TIMEOUT = 20


def fetch(url, *, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "zero-slop-release-check"})
    last_error = None
    for _attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                body = response.read()
                return body if binary else body.decode()
        except urllib.error.HTTPError:
            # A server response is authoritative. Retrying a 404 and later
            # calling it "offline" hid the missing v2.8.4 release ZIP.
            raise
        except Exception as exc:  # DNS, timeout, TLS, or disconnected network
            last_error = exc
    raise last_error or RuntimeError("unreachable")


def _unreachable(exc):
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError)) \
        and not isinstance(exc, urllib.error.HTTPError)


def check_once(*, fetch_fn=fetch, emit=print):
    """Return ``(problems, skipped)`` for one external-state snapshot."""
    shipped = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    emit(f"this repo ships           {shipped}")
    problems, skipped = [], []

    release_url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        release = json.loads(fetch_fn(release_url))
        tag = release.get("tag_name", "")
        emit(f"newest GitHub release     {tag}")
        if tag.lstrip("v") != shipped:
            problems.append(
                f"the newest GitHub release is {tag or 'unnamed'}, not v{shipped}."
            )
    except urllib.error.HTTPError as exc:
        problems.append(f"the GitHub release endpoint returned HTTP {exc.code}.")
    except Exception as exc:
        if _unreachable(exc):
            skipped.append(f"GitHub releases ({exc})")
        else:
            problems.append(f"the GitHub release response is invalid ({exc}).")

    zip_url = f"https://github.com/{REPO}/releases/latest/download/zero-slop.zip"
    try:
        blob = fetch_fn(zip_url, binary=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            names = [name for name in archive.namelist() if name.endswith("SKILL.md")]
            if len(names) != 1:
                raise ValueError(f"expected one SKILL.md, found {len(names)}")
            match = re.search(
                r'version:\s*"([0-9.]+)"', archive.read(names[0]).decode()
            )
            if not match:
                raise ValueError("SKILL.md has no version")
            inside = match.group(1)
        emit(f"inside that release's ZIP {inside}")
        if inside != shipped:
            problems.append(
                f"releases/latest/download/zero-slop.zip contains {inside}, not {shipped}."
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            problems.append("the GitHub release ZIP is missing (HTTP 404).")
        else:
            problems.append(f"the GitHub release ZIP returned HTTP {exc.code}.")
    except Exception as exc:
        if _unreachable(exc):
            skipped.append(f"release ZIP ({exc})")
        else:
            problems.append(f"the GitHub release ZIP is invalid ({exc}).")

    npm_tarball_url = None
    try:
        metadata = json.loads(fetch_fn("https://registry.npmjs.org/zero-slop/latest"))
        published = metadata.get("version")
        emit(f"published to npm          {published}")
        if published != shipped:
            problems.append(f"npm publishes {published or 'no version'}, not {shipped}.")
        else:
            npm_tarball_url = metadata.get("dist", {}).get("tarball")
            if not isinstance(npm_tarball_url, str) or not npm_tarball_url.startswith("https://"):
                problems.append("the npm package metadata has no HTTPS tarball URL.")
    except urllib.error.HTTPError as exc:
        problems.append(f"the npm package endpoint returned HTTP {exc.code}.")
    except Exception as exc:
        if _unreachable(exc):
            skipped.append(f"npm ({exc})")
        else:
            problems.append(f"the npm package response is invalid ({exc}).")

    if npm_tarball_url:
        try:
            blob = fetch_fn(npm_tarball_url, binary=True)
            with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
                names = set(archive.getnames())

                def read_member(name):
                    member = archive.extractfile(name)
                    if member is None:
                        raise ValueError(f"{name} is not a regular file")
                    return member.read()

                required = {
                    "package/package.json",
                    "package/SKILL.md",
                    "package/bin/zero-slop.mjs",
                }
                missing = sorted(required - names)
                if missing:
                    raise ValueError(f"missing {', '.join(missing)}")
                package = json.loads(read_member("package/package.json"))
                package_version = package.get("version")
                command = package.get("bin", {}).get("zero-slop") \
                    if isinstance(package.get("bin"), dict) else package.get("bin")
                skill_match = re.search(
                    rb'version:\s*"([0-9.]+)"', read_member("package/SKILL.md")
                )
                if not skill_match:
                    raise ValueError("package/SKILL.md has no version")
                skill_version = skill_match.group(1).decode()
                if command != "bin/zero-slop.mjs":
                    raise ValueError(f"zero-slop command points to {command!r}")
                if package_version != skill_version:
                    raise ValueError(
                        f"package.json says {package_version}, SKILL.md says {skill_version}"
                    )
            emit(f"inside npm package        {package_version}")
            if package_version != shipped:
                problems.append(
                    f"the npm tarball contains {package_version}, not {shipped}."
                )
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                problems.append("the npm package tarball is missing (HTTP 404).")
            else:
                problems.append(f"the npm package tarball returned HTTP {exc.code}.")
        except Exception as exc:
            if _unreachable(exc):
                skipped.append(f"npm package tarball ({exc})")
            else:
                problems.append(f"the npm package tarball is invalid ({exc}).")

    return problems, skipped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--require-network", action="store_true",
        help="fail rather than skip when a published service is unreachable",
    )
    parser.add_argument(
        "--wait-seconds", type=int, default=0, metavar="N",
        help="wait up to N seconds for GitHub and npm publication to converge",
    )
    args = parser.parse_args(argv)
    if args.wait_seconds < 0 or args.wait_seconds > 900:
        parser.error("--wait-seconds must be between 0 and 900")

    deadline = time.monotonic() + args.wait_seconds
    attempt = 0
    while True:
        attempt += 1
        if attempt > 1:
            print(f"\npublication check {attempt}")
        problems, skipped = check_once()
        effective = list(problems)
        if args.require_network:
            effective.extend(f"required service was unreachable: {item}" for item in skipped)
        if not effective:
            for item in skipped:
                print(f"skipped: {item}")
            if not skipped:
                print("\nEvery published surface advertises the version this repo ships.")
            return 0
        if time.monotonic() >= deadline:
            for item in skipped:
                print(f"skipped: {item}")
            print()
            for problem in effective:
                print(f"DRIFT: {problem}")
            return 1
        remaining = max(0, int(deadline - time.monotonic()))
        print(f"publication has not converged; retrying in 15 seconds ({remaining}s remain)")
        time.sleep(min(15, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    sys.exit(main())
