#!/usr/bin/env python3
"""Confirm that published packages, the website, and live MCP match this repository.

The check distinguishes an unreachable service from a reachable service with a
missing or stale artifact. Offline developer runs may skip unreachable hosts;
release automation uses ``--require-network`` and a bounded wait so publication
latency cannot be mistaken for either success or permanent drift.
"""
import argparse
import base64
import gzip
import hashlib
import io
import json
import re
import stat
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
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_UNPACKED_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 1024
WEBSITE = "https://zero-slop.ai/"
MCP = "https://mcp.zero-slop.ai"
HOMEBREW = "https://raw.githubusercontent.com/manavmishra/homebrew-zero-slop/main/Formula/zero-slop.rb"
WEBSITE_DOWNLOAD_HOSTS = {"zero-slop.ai", "www.zero-slop.ai", "github.com"}
BROWSER_FILES = {
    "scorer": "scripts/slopscore.py", "safeio": "scripts/safeio.py",
    "register": "scripts/register.py", "rerank": "scripts/rerank.py",
    "rescue": "scripts/rescue.py", "patterns": "data/patterns.json",
    "learned": "data/learned.json",
}


def expected_payloads():
    """Use the build's runtime allowlist; do not rebuild or read private state."""
    from build_plugin import ITEMS, wanted
    skill = {}
    for item in ITEMS:
        source = ROOT / item
        if source.is_symlink() or not source.exists():
            raise ValueError(f"unsafe or missing canonical runtime: {item}")
        if source.is_dir() and any(path.is_symlink() for path in source.rglob("*")):
            raise ValueError(f"symlink in canonical runtime: {item}")
        paths = [source] if source.is_file() else wanted(source)
        for path in paths:
            skill[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    npm = dict(skill)
    for path in (ROOT / "bin").rglob("*"):
        if path.is_symlink():
            raise ValueError("symlink in canonical CLI")
        if path.is_file():
            npm[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for name in ("package.json", "plugin.json", "mcp.json", ".mcp.json", "gemini-extension.json",
                 "docs/cli.md", "docs/rest-api.md", "README.md", "SECURITY.md", "LICENSE"):
        npm[name] = (ROOT / name).read_bytes()
    return skill, npm


def _member_name(name):
    if (not name or name.startswith("/") or "\\" in name or "\x00" in name
            or any(part in ("", ".", "..") for part in name.rstrip("/").split("/"))):
        raise ValueError("unsafe archive member path")
    return name.rstrip("/")


def _read_member(member, size, name):
    limit = MAX_SKILL_BYTES if name.rsplit("/", 1)[-1] == "SKILL.md" else MAX_MEMBER_BYTES
    if size < 0 or size > limit:
        raise ValueError(f"{name} exceeds the uncompressed size limit")
    content = member.read(limit + 1)
    if len(content) > limit or len(content) != size:
        raise ValueError(f"{name} has an invalid or oversized uncompressed size")
    return content


def _zip_files(blob):
    """Never extract or execute an archive. Bound every read and total output."""
    if len(blob) > MAX_DOWNLOAD_BYTES:
        raise ValueError("ZIP exceeds the download size limit")
    files, seen, total = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        if len(archive.infolist()) > MAX_ARCHIVE_MEMBERS:
            raise ValueError("too many ZIP members")
        for info in archive.infolist():
            name = _member_name(info.filename)
            if name in seen:
                raise ValueError("duplicate ZIP member")
            seen.add(name)
            mode = stat.S_IFMT(info.external_attr >> 16)
            if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("ZIP contains a non-regular member")
            if info.is_dir():
                continue
            if mode == stat.S_IFDIR:
                raise ValueError("ZIP directory has a file name")
            total += info.file_size
            if total > MAX_UNPACKED_BYTES:
                raise ValueError("ZIP exceeds the total uncompressed size limit")
            with archive.open(info) as member:
                files[name] = _read_member(member, info.file_size, name)
    return files


def _tar_files(blob):
    if len(blob) > MAX_DOWNLOAD_BYTES:
        raise ValueError("tarball exceeds the download size limit")
    # Bounding gzip output first also bounds tar headers and extended metadata.
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as compressed:
        unpacked = compressed.read(MAX_UNPACKED_BYTES + 1)
    if len(unpacked) > MAX_UNPACKED_BYTES:
        raise ValueError("tarball exceeds the total uncompressed size limit")
    files, seen = {}, set()
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as archive:
        for index, info in enumerate(archive):
            if index >= MAX_ARCHIVE_MEMBERS:
                raise ValueError("too many tarball members")
            name = _member_name(info.name)
            if name in seen:
                raise ValueError("duplicate tarball member")
            seen.add(name)
            if info.isdir():
                continue
            if not info.isfile():
                raise ValueError("tarball contains a non-regular member")
            with archive.extractfile(info) as member:
                files[name] = _read_member(member, info.size, name)
    return files


def _same_payload(actual, expected, *, prefix):
    selected = {name[len(prefix):]: content for name, content in actual.items()
                if name.startswith(prefix)}
    missing = sorted(set(expected) - set(selected))
    extra = sorted(set(selected) - set(expected))
    if missing or extra or len(selected) != len(actual):
        raise ValueError(f"runtime file set differs (missing {missing[:5]}, unexpected {extra[:5]})")
    changed = [name for name, content in expected.items()
               if hashlib.sha256(selected[name]).digest() != hashlib.sha256(content).digest()]
    if changed:
        raise ValueError(f"runtime bytes differ: {', '.join(sorted(changed)[:5])}")


def _skill_version(skill_bytes):
    skill = skill_bytes.decode()
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", skill, re.S)
    versions = re.findall(r'^\s*version:\s*"([^"\r\n]+)"[ \t]*$',
                          frontmatter.group(1), re.M) if frontmatter else []
    if len(versions) != 1:
        raise ValueError("SKILL.md must have one quoted version in its frontmatter")
    return versions[0]


def _zip_skill_version(blob):
    """Read the packaged skill's frontmatter without extracting archive files."""
    files = _zip_files(blob)
    names = [name for name in files if name.rsplit("/", 1)[-1] == "SKILL.md"]
    if len(names) != 1:
        raise ValueError(f"expected one SKILL.md, found {len(names)}")
    return _skill_version(files[names[0]])


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


def check_once(*, fetch_fn=fetch, emit=print, skip_website=False, skip_homebrew=False):
    """Return ``(problems, skipped)`` for one external-state snapshot."""
    shipped = json.loads((ROOT / "package.json").read_text())["version"]
    skill_payload, npm_payload = expected_payloads()
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
        else:
            _same_payload(_zip_files(blob), skill_payload, prefix="zero-slop/")
            emit(f"release ZIP runtime       {len(skill_payload)} files match SHA-256")
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

    npm_tarball_url, npm_blob, npm_integrity = None, None, None
    expected_npm_url = f"https://registry.npmjs.org/zero-slop/-/zero-slop-{shipped}.tgz"
    try:
        metadata = json.loads(fetch_fn("https://registry.npmjs.org/zero-slop/latest"))
        published = metadata.get("version")
        emit(f"published to npm          {published}")
        if published != shipped:
            problems.append(f"npm publishes {published or 'no version'}, not {shipped}.")
        else:
            dist = metadata.get("dist", {})
            if dist.get("tarball") != expected_npm_url:
                raise ValueError("the npm tarball URL is not the exact official versioned URL")
            npm_tarball_url = expected_npm_url
            npm_integrity = dist.get("integrity")
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
            npm_blob = blob
            integrity = "sha512-" + base64.b64encode(hashlib.sha512(blob).digest()).decode()
            if npm_integrity != integrity:
                raise ValueError("npm dist.integrity is missing or does not match tarball SHA-512")
            files = _tar_files(blob)
            required = {"package/package.json", "package/SKILL.md", "package/bin/zero-slop.mjs"}
            missing = sorted(required - set(files))
            if missing:
                raise ValueError(f"missing {', '.join(missing)}")
            package = json.loads(files["package/package.json"])
            package_version = package.get("version")
            command = package.get("bin", {}).get("zero-slop") \
                if isinstance(package.get("bin"), dict) else package.get("bin")
            skill_version = _skill_version(files["package/SKILL.md"])
            if command != "bin/zero-slop.mjs":
                raise ValueError(f"zero-slop command points to {command!r}")
            if package_version != skill_version:
                raise ValueError(f"package.json says {package_version}, SKILL.md says {skill_version}")
            emit(f"inside npm package        {package_version}")
            if package_version != shipped:
                problems.append(
                    f"the npm tarball contains {package_version}, not {shipped}."
                )
            else:
                _same_payload(files, npm_payload, prefix="package/")
                emit(f"npm runtime and CLI       {len(npm_payload)} files match SHA-256")
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

    if not skip_homebrew:
        try:
            formula = fetch_fn(HOMEBREW)
            urls = re.findall(r'^\s*url "([^"\r\n]+)"\s*$', formula, re.M)
            checksums = re.findall(r'^\s*sha256 "([a-f0-9]{64})"\s*$', formula, re.M)
            versions = re.findall(r'^\s*version "([^"\r\n]+)"\s*$', formula, re.M)
            declarations = re.findall(r'^[ \t]*version\b[^\r\n]*', formula, re.M)
            if len(declarations) != len(versions):
                raise ValueError("formula version declaration is not in the expected literal format")
            if urls != [expected_npm_url] or (versions and versions != [shipped]):
                raise ValueError(f"formula must install the official npm tarball for {shipped}")
            if len(checksums) != 1:
                raise ValueError("formula must declare exactly one SHA-256")
            # Reuse the downloaded artifact; an unavailable npm latest endpoint
            # must not prevent checking the formula's exact versioned package.
            brew_blob = npm_blob if npm_blob is not None else fetch_fn(expected_npm_url, binary=True)
            if checksums[0] != hashlib.sha256(brew_blob).hexdigest():
                raise ValueError("formula SHA-256 does not match the npm tarball bytes")
            emit(f"Homebrew formula          {shipped}, npm SHA-256 matches")
        except urllib.error.HTTPError as exc:
            problems.append(f"the Homebrew formula or tarball returned HTTP {exc.code}.")
        except Exception as exc:
            if _unreachable(exc):
                skipped.append(f"Homebrew ({exc})")
            else:
                problems.append(f"the Homebrew formula is invalid ({exc}).")

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
        elif record.get("remotes") != [{"type": "streamable-http", "url": f"{MCP}/mcp"}]:
            raise ValueError("the official MCP endpoint must be the canonical Streamable HTTP /mcp URL")
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

    try:
        document = json.loads(fetch_fn(f"{MCP}/openapi.json"))
        info = document.get("info") if isinstance(document, dict) else None
        if not isinstance(info, dict) or info.get("title") != "Zero Slop API":
            raise ValueError("expected Zero Slop API info metadata")
        version = info.get("version")
        if version != shipped:
            raise ValueError(f"REST OpenAPI serves {version or 'no version'}, not {shipped}")
        if document.get("servers") != [{"url": MCP}]:
            raise ValueError("REST OpenAPI must advertise only the canonical HTTPS server")
        post = document.get("paths", {}).get("/v1/deslop", {}).get("post", {})
        if post.get("operationId") != "deslop":
            raise ValueError("REST OpenAPI is missing the official POST /v1/deslop operation")
        emit(f"live REST OpenAPI         {version}, official endpoint matches")
    except urllib.error.HTTPError as exc:
        problems.append(f"the live REST OpenAPI returned HTTP {exc.code}.")
    except Exception as exc:
        if _unreachable(exc):
            skipped.append(f"live REST OpenAPI ({exc})")
        else:
            problems.append(f"the live REST OpenAPI is invalid ({exc}).")

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
            else:
                hashes = live.get("files")
                if not isinstance(hashes, dict):
                    raise ValueError("browser runtime manifest is missing file hashes")
                for key, path in BROWSER_FILES.items():
                    expected_hash = hashlib.sha256(skill_payload[path]).hexdigest()
                    if hashes.get(key) != expected_hash:
                        raise ValueError(f"browser runtime manifest hash differs: {path}")
                for path in BROWSER_FILES.values():
                    content = fetch_fn(f"{WEBSITE}try-runtime/zero-slop/{path}", binary=True)
                    if (len(content) > MAX_MEMBER_BYTES
                            or hashlib.sha256(content).digest() != hashlib.sha256(skill_payload[path]).digest()):
                        raise ValueError(f"served browser runtime bytes differ: {path}")
                emit(f"website browser runtime   {len(BROWSER_FILES)} files match SHA-256")
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
                blob = fetch_fn(website_zip_url, binary=True)
                inside = _zip_skill_version(blob)
                emit(f"inside website's ZIP     {inside}")
                if inside != shipped:
                    problems.append(f"the website ZIP contains {inside}, not {shipped}.")
                else:
                    _same_payload(_zip_files(blob), skill_payload, prefix="zero-slop/")
                    emit(f"website ZIP runtime       {len(skill_payload)} files match SHA-256")
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
    parser.add_argument(
        "--skip-homebrew", action="store_true",
        help="allow tap publication to converge separately; scheduled full checks must omit this flag",
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
        problems, skipped = check_once(skip_website=args.skip_website,
                                       skip_homebrew=args.skip_homebrew)
        effective = list(problems)
        if args.require_network:
            effective.extend(f"required service was unreachable: {item}" for item in skipped)
        if not effective:
            for item in skipped:
                print(f"skipped: {item}")
            if not skipped:
                print("\nAll checked release versions, endpoints, and runtime payloads match this repo.")
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
