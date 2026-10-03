#!/usr/bin/env python3
"""Build a clean Claude/Codex marketplace folder from the canonical runtime.

    python3 scripts/build_marketplace_package.py
    python3 scripts/build_marketplace_package.py --check
    python3 scripts/build_marketplace_package.py --zip

The folder is distribution/plugins/zero-slop; --zip also creates the ignored
tmp/zero-slop-marketplace.zip, with .codex-plugin at archive root. This offline
maintainer tool never changes the root or skills/zero-slop install layouts.
Local ownership hashes in tmp permit deletion only of unmodified obsolete files
from a previous build. Unknown files require review, never recursive deletion.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile

from build_plugin import ITEMS, wanted
from safeio import atomic_write_bytes

ROOT = Path(__file__).resolve().parent.parent
DEST = Path("distribution/plugins/zero-slop")
ZIP = Path("tmp/zero-slop-marketplace.zip")
STATE = Path("tmp/zero-slop-marketplace-files.json")
MCP_URL = "https://mcp.zero-slop.ai/mcp"
SUPPORT_FILES = (
    ".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
    "LICENSE", "README.md", "SECURITY.md", ".mcp.json", "mcp.json",
)
MAX_BYTES = 1024 * 1024
ICON_KEYS = ("icon", "smallIcon", "largeIcon", "composerIcon", "composerIconDark", "logo", "logoDark")


def safe_path(value: str) -> Path:
    """Accept one canonical relative POSIX path; reject traversal and aliases."""
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"invalid package path: {value!r}")
    parsed = PurePosixPath(value)
    if (parsed.is_absolute() or value != parsed.as_posix()
            or any(part in (".", "..") for part in parsed.parts)):
        raise ValueError(f"invalid package path: {value!r}")
    return Path(*parsed.parts)


def guarded(root: Path, relative: str | Path) -> Path:
    path = root / safe_path(str(relative))
    for candidate in (root, *root.parents, *path.parents):
        if candidate.is_symlink():
            raise ValueError(f"refusing symlink: {candidate}")
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"refusing unsafe path: {path}")
    return path


def read_source(root: Path, relative: str) -> bytes:
    path = guarded(root, relative)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError(f"missing, non-file, or oversized source: {relative}")
    return path.read_bytes()


def payload(root: Path) -> dict[str, bytes]:
    files = {name: read_source(root, name) for name in SUPPORT_FILES}
    for item in ITEMS:
        source = guarded(root, item)
        if not source.exists():
            raise ValueError(f"missing runtime source: {item}")
        if source.is_dir():
            if any(path.is_symlink() for path in source.rglob("*")):
                raise ValueError(f"symlink in runtime source: {item}")
            sources = wanted(source)
        else:
            sources = [source]
        for path in sources:
            relative = path.relative_to(root).as_posix()
            if (path.suffix not in (".py", ".json", ".md", ".txt")
                    or path.name.lower() in ("package-lock.json", "npm-shrinkwrap.json", "credentials.json", "secrets.json", "auth.json")
                    or path.name.startswith(".")):
                raise ValueError(f"unexpected runtime file: {relative}")
            files[f"skills/zero-slop/{relative}"] = read_source(root, relative)
    for manifest_name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        manifest = json.loads(files[manifest_name])
        if manifest.get("skills") != "./skills/":
            raise ValueError(f"unexpected skill path in {manifest_name}")
        accepted_mcp = {"./.mcp.json"} if manifest_name.startswith(".claude") else {"./mcp.json", "./.mcp.json"}
        if manifest.get("mcpServers") not in accepted_mcp:
            raise ValueError(f"unexpected MCP path in {manifest_name}")
        if manifest_name.startswith(".codex") and manifest["mcpServers"] != "./.mcp.json":
            # Codex submissions use the native HTTP config, not the portable
            # Agent Plugins config. Do not mutate the canonical root manifest.
            manifest["mcpServers"] = "./.mcp.json"
            files[manifest_name] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
        for section in (manifest, manifest.get("interface", {})):
            for key in ICON_KEYS:
                if key not in section:
                    continue
                value = section[key]
                if not isinstance(value, str) or not value.startswith("./"):
                    raise ValueError(f"icon must be a plugin-relative path: {value!r}")
                relative = safe_path(value[2:]).as_posix()
                if (relative not in (".claude-plugin/icon.svg", ".codex-plugin/icon.svg")
                        and not relative.startswith("assets/logo/")):
                    raise ValueError(f"icon must come from the approved logo assets: {relative}")
                if Path(relative).suffix not in (".svg", ".png"):
                    raise ValueError(f"unsupported icon format: {relative}")
                files[relative] = read_source(root, relative)
    for name, transport in ((".mcp.json", "http"), ("mcp.json", "streamable-http")):
        config = json.loads(files[name])
        if config.get("mcpServers") != {"zero-slop": {"type": transport, "url": MCP_URL}}:
            raise ValueError(f"unexpected MCP server or credentials in {name}")
    return dict(sorted(files.items()))


def archive_bytes(files: dict[str, bytes], openai_existing_name: str | None = None) -> bytes:
    if openai_existing_name is not None:
        if (len(openai_existing_name) > 64 or
                not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", openai_existing_name)):
            raise ValueError("invalid existing OpenAI package name")
        files = dict(files)
        manifest = json.loads(files[".codex-plugin/plugin.json"])
        manifest["name"] = openai_existing_name
        files[".codex-plugin/plugin.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    buffer = io.BytesIO()
    # Stored entries avoid dependence on a compressor version or platform.
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(files.items()):
            safe_path(name)
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, content)
    return buffer.getvalue()


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build(root: Path = ROOT, *, check: bool = False, make_zip: bool = False,
          openai_existing_name: str | None = None) -> int:
    root = Path(root).absolute()
    try:
        files = payload(root)
        if openai_existing_name and not make_zip:
            raise ValueError("--openai-existing-name requires --zip")
        zip_contents = archive_bytes(files, openai_existing_name) if make_zip else None
        destination = guarded(root, DEST)
        state_path = guarded(root, STATE)
        zip_path = guarded(root, ZIP)
        # Validate all output parents before making any writes.
        for name in files:
            guarded(root, DEST / safe_path(name))
        actual = {}
        noncanonical_modes = set()
        actual_dirs = set()
        if destination.exists():
            for path in destination.rglob("*"):
                guarded(root, path.relative_to(root))
                if path.is_dir():
                    actual_dirs.add(path.relative_to(destination).as_posix())
                    continue
                if not path.is_file() or path.stat().st_size > MAX_BYTES:
                    raise ValueError(f"non-file or oversized package entry: {path}")
                actual[path.relative_to(destination).as_posix()] = path.read_bytes()
                if stat.S_IMODE(path.stat().st_mode) != 0o644:
                    noncanonical_modes.add(path.relative_to(destination).as_posix())
        stale = sorted(set(actual) - set(files))
        expected_dirs = {parent.as_posix() for name in files for parent in safe_path(name).parents
                         if parent != Path(".")}
        stale_dirs = actual_dirs - expected_dirs
        changed = sorted(name for name, content in files.items()
                         if actual.get(name) != content or name in noncanonical_modes)
        if check:
            if stale or changed or stale_dirs:
                raise ValueError("marketplace package is stale: " + ", ".join(stale + changed + sorted(stale_dirs)))
            if make_zip and (not zip_path.is_file() or zip_path.read_bytes() != zip_contents):
                raise ValueError("marketplace ZIP is stale")
            print(f"marketplace package is current ({len(files)} files)")
            return 0
        previous = json.loads(state_path.read_bytes()) if state_path.exists() else {}
        if not isinstance(previous, dict):
            raise ValueError("invalid local package ownership record")
        owned_dirs = {parent.as_posix() for name in previous for parent in safe_path(name).parents
                      if parent != Path(".")}
        if stale_dirs - owned_dirs:
            raise ValueError("refusing to remove unowned directories: " + ", ".join(sorted(stale_dirs - owned_dirs)))
        # Unknown or modified obsolete files are not ours to delete.
        for name in stale:
            if previous.get(name) != digest(actual[name]):
                raise ValueError(f"refusing to delete unowned or modified file: {name}")
        for name in changed:
            atomic_write_bytes(guarded(root, DEST / safe_path(name)), files[name], mode=0o644)
        for name in stale:
            guarded(root, DEST / safe_path(name)).unlink()
        for name in sorted(stale_dirs, key=lambda name: len(Path(name).parts), reverse=True):
            path = guarded(root, DEST / safe_path(name))
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        atomic_write_bytes(state_path, (json.dumps({name: digest(content) for name, content in files.items()},
                                                 indent=2, sort_keys=True) + "\n").encode(), mode=0o644)
        if make_zip:
            atomic_write_bytes(zip_path, zip_contents, mode=0o644)
        print(f"built {len(files)} files in {DEST}" + (f" and {ZIP}" if make_zip else ""))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"marketplace package error: {exc}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="read-only freshness guard")
    parser.add_argument("--zip", action="store_true", help="also build/check the local OpenAI ZIP")
    parser.add_argument("--openai-existing-name", help="preserve a dashboard-assigned name in the ZIP only")
    args = parser.parse_args(argv)
    return build(check=args.check, make_zip=args.zip, openai_existing_name=args.openai_existing_name)


if __name__ == "__main__":
    sys.exit(main())
