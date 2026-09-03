#!/usr/bin/env python3
"""Copy the exact shipped scorer into the private Python Worker bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "mcp" / "scorer" / "src"
SOURCES = {
    ROOT / "scripts" / "slopscore.py": DEST / "engine" / "slopscore.py",
    ROOT / "scripts" / "register.py": DEST / "engine" / "register.py",
    ROOT / "scripts" / "rerank.py": DEST / "engine" / "rerank.py",
    ROOT / "scripts" / "safeio.py": DEST / "engine" / "safeio.py",
    ROOT / "data" / "patterns.json": DEST / "data" / "patterns.json",
    ROOT / "data" / "learned.json": DEST / "data" / "learned.json",
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_manifest(version: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    manifest["version"] = version
    for source, target in SOURCES.items():
        manifest[str(source.relative_to(ROOT))] = digest(source)
    return manifest


def current_manifest() -> dict[str, str]:
    path = DEST / "scorer-manifest.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                              for k, v in value.items()):
        raise ValueError("scorer manifest must contain string keys and values")
    return value


def check_bundle(manifest: dict[str, str]) -> int:
    expected = expected_manifest(manifest.get("version", ""))
    errors: list[str] = []
    if manifest != expected:
        errors.append("manifest hashes do not match the current scorer sources")
    for source, target in SOURCES.items():
        source_name = str(source.relative_to(ROOT))
        if not target.exists() or digest(target) != manifest.get(source_name):
            errors.append(f"vendored scorer differs: {target.relative_to(ROOT)}")
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"Scorer bundle is byte-for-byte pinned to Zero Slop {manifest['version']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without writing")
    parser.add_argument("--version", help="release version to record during an explicit sync")
    args = parser.parse_args()

    manifest = current_manifest()
    if args.check:
        if args.version:
            parser.error("--version cannot be combined with --check")
        return check_bundle(manifest)

    if not args.version or not VERSION_RE.fullmatch(args.version):
        parser.error("an explicit semantic --version is required when syncing")

    for source, target in SOURCES.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    manifest = expected_manifest(args.version)
    manifest_path = DEST / "scorer-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Synced Zero Slop {manifest['version']} into {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
