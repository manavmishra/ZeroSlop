#!/usr/bin/env python3
"""Confirm that published packages, the website, and live MCP match this repository.

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
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit

ROOT = Path(__file__).resolve().parent.parent
REPO = "manavmishra/ZeroSlop"
TIMEOUT = 20
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 32 * 1024 * 1024
MAX_SKILL_BYTES = 256 * 1024
WEBSITE = "https://zero-slop.ai/"
MCP = "https://mcp.zero-slop.ai"
WEBSITE_DOWNLOAD_HOSTS = {"zero-slop.ai", "www.zero-slop.ai", "github.com"}


def _zip_skill_version(blob):
    """Read the packaged skill's frontmatter without extracting archive files."""
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = [name for name in archive.namelist() if Path(name).name == "SKILL.md"]
        if len(names) != 1:
            raise ValueError(f"expected one SKILL.md, found {len(names)}")
        if archive.getinfo(names[0]).file_size > MAX_SKILL_BYTES:
            raise ValueError("SKILL.md exceeds the uncompressed size limit")
        with archive.open(names[0]) as member:
            skill_bytes = member.read(MAX_SKILL_BYTES + 1)
        if len(skill_bytes) > MAX_SKILL_BYTES:
            raise ValueError("SKILL.md exceeds the uncompressed size limit")
        skill = skill_bytes.decode()
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", skill, re.S)
    versions = re.findall(r'^\s*version:\s*"([^"\r\n]+)"[ \t]*$',
                          frontmatter.group(1), re.M) if frontmatter else []
    if len(versions) != 1:
        raise ValueError("SKILL.md must have one quoted version in its frontmatter")
    return versions[0]


class _DownloadLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.base = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        href = attrs.get("href")
        if not href:
            return
        if tag == "base" and self.base is None:
            self.base = href
        if tag == "a" and urlsplit(href).path.lower().endswith(".zip"):
            self.links.append(href)


def _website_zip_url(html):
    """Follow the installer offered by the page, not an assumed release URL."""
    parser = _DownloadLinks()
    parser.feed(html)
    parser.close()
    base = urljoin(WEBSITE, parser.base or "")
    links = {urldefrag(urljoin(base, href))[0] for href in parser.links}
    if len(links) != 1:
        raise ValueError(f"expected one distinct ZIP download link, found {len(links)}")
    url = links.pop()
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in WEBSITE_DOWNLOAD_HOSTS
            or parsed.port not in (None, 443)
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("the ZIP download link must use HTTPS on an approved host without credentials")
    return url


def fetch(url, *, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "zero-slop-release-check"})
    last_error = None
    for _attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                limit = MAX_DOWNLOAD_BYTES if binary else MAX_METADATA_BYTES
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise ValueError(f"response exceeds the {limit}-byte size limit")
                return body if binary else body.decode()
        except (urllib.error.HTTPError, ValueError):
            # A server response is authoritative. Retrying a 404 and later
            # calling it "offline" hid the missing v2.8.4 release ZIP.
            raise
        except Exception as exc:  # DNS, timeout, TLS, or disconnected network
            last_error = exc
    raise last_error or RuntimeError("unreachable")


def _unreachable(exc):
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError)) \
        and not isinstance(exc, urllib.error.HTTPError)


def check_once(*, fetch_fn=fetch, emit=print, skip_website=False):
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
        inside = _zip_skill_version(blob)
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

    try:
        registry = json.loads(fetch_fn(
            "https://registry.modelcontextprotocol.io/v0.1/servers/"
            "io.github.manavmishra%2Fzero-slop/versions/latest"
        ))
        record = registry.get("server") if isinstance(registry, dict) else None
        if not isinstance(record, dict) or record.get("name") != "io.github.manavmishra/zero-slop":
            raise ValueError("the latest record does not identify the Zero Slop server")
        official = registry.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
        if official.get("status") != "active" or official.get("isLatest") is not True:
            raise ValueError("the latest record is not marked active and latest")
        registry_version = record.get("version")
        emit(f"official MCP Registry    {registry_version}")
        if registry_version != shipped:
            problems.append(
                f"the official MCP Registry serves {registry_version or 'no version'}, not {shipped}."
            )
    except urllib.error.HTTPError as exc:
        problems.append(f"the MCP Registry returned HTTP {exc.code}.")
    except Exception as exc:
        if _unreachable(exc):
            skipped.append(f"MCP Registry ({exc})")
        else:
            problems.append(f"the MCP Registry response is invalid ({exc}).")

    try:
        health = json.loads(fetch_fn(f"{MCP}/health"))
        if not isinstance(health, dict) or health.get("service") != "zero-slop-mcp":
            raise ValueError("expected zero-slop-mcp health metadata")
        scorer = health.get("scorer")
        if not isinstance(scorer, dict):
            raise ValueError("missing scorer health metadata")
        for label, version in (("gateway", health.get("version")),
                               ("scorer", scorer.get("scorerVersion"))):
            emit(f"live MCP {label:16} {version}")
            if version != shipped:
                problems.append(
                    f"the live MCP {label} serves {version or 'no version'}, not {shipped}."
                )
        if (health.get("ok") is not True or scorer.get("ok") is not True
                or health.get("editorConfigured") is not True):
            problems.append("the live MCP health is degraded or missing healthy readiness flags.")
    except urllib.error.HTTPError as exc:
        problems.append(f"the live MCP health endpoint returned HTTP {exc.code}.")
    except Exception as exc:
        if _unreachable(exc):
            skipped.append(f"live MCP health ({exc})")
        else:
            problems.append(f"the live MCP health response is invalid ({exc}).")

    try:
        card = json.loads(fetch_fn(f"{MCP}/.well-known/mcp/server-card.json"))
        info = card.get("serverInfo") if isinstance(card, dict) else None
        if not isinstance(info, dict) or info.get("name") != "zero-slop":
            raise ValueError("expected zero-slop serverInfo metadata")
        version = info.get("version")
        emit(f"live MCP server-card     {version}")
        if version != shipped:
            problems.append(
                f"the live MCP server-card serves {version or 'no version'}, not {shipped}."
            )
    except urllib.error.HTTPError as exc:
        problems.append(f"the live MCP server-card returned HTTP {exc.code}.")
    except Exception as exc:
        if _unreachable(exc):
            skipped.append(f"live MCP server-card ({exc})")
        else:
            problems.append(f"the live MCP server-card response is invalid ({exc}).")

    if not skip_website:
        try:
            live = json.loads(fetch_fn(
                f"https://zero-slop.ai/try-runtime/manifest.json?release-check={int(time.time())}"
            ))
            live_version = live.get("skillVersion")
            emit(f"served by zero-slop.ai  {live_version}")
            if live_version != shipped:
                problems.append(
                    f"zero-slop.ai serves {live_version or 'no version'}, not {shipped}."
                )
        except urllib.error.HTTPError as exc:
            problems.append(f"the live website manifest returned HTTP {exc.code}.")
        except Exception as exc:
            if _unreachable(exc):
                skipped.append(f"zero-slop.ai ({exc})")
            else:
                problems.append(f"the live website manifest is invalid ({exc}).")

        website_zip_url = None
        try:
            website_zip_url = _website_zip_url(fetch_fn(WEBSITE))
            emit(f"website download URL     {website_zip_url}")
        except urllib.error.HTTPError as exc:
            problems.append(f"the website download page returned HTTP {exc.code}.")
        except Exception as exc:
            if _unreachable(exc):
                skipped.append(f"website download page ({exc})")
            else:
                problems.append(f"the website download link is invalid ({exc}).")

        if website_zip_url:
            try:
                inside = _zip_skill_version(fetch_fn(website_zip_url, binary=True))
                emit(f"inside website's ZIP     {inside}")
                if inside != shipped:
                    problems.append(f"the website ZIP contains {inside}, not {shipped}.")
            except urllib.error.HTTPError as exc:
                problems.append(f"the website ZIP returned HTTP {exc.code}.")
            except Exception as exc:
                if _unreachable(exc):
                    skipped.append(f"website ZIP ({exc})")
                else:
                    problems.append(f"the website ZIP is invalid ({exc}).")

    return problems, skipped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--require-network", action="store_true",
        help="fail rather than skip when a published service is unreachable",
    )
    parser.add_argument(
        "--wait-seconds", type=int, default=0, metavar="N",
        help="wait up to N seconds for the published release surfaces to converge",
    )
    parser.add_argument(
        "--skip-website", action="store_true",
        help="leave website convergence to the website repository's own release gate",
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
        problems, skipped = check_once(skip_website=args.skip_website)
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
