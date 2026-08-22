#!/usr/bin/env python3
"""build_skill_zip — package the skill as a single-skill zip for claude.ai upload.

claude.ai's "upload a skill" accepts a zip that contains exactly one skill, and
it decides that by counting SKILL.md files. This repo has two on purpose: one at
the root for a plain `git clone`, and one under skills/zero-slop/ for the plugin
system. A zip of the whole repo therefore looks like two skills and is rejected.

This writes dist/zero-slop.zip containing only the skills/zero-slop/ folder, which
holds a single SKILL.md next to its references, scripts and data. That is the file
to upload under Settings, Capabilities, Skills.

    python3 scripts/build_skill_zip.py            # rebuild the zip
    python3 scripts/build_skill_zip.py --check    # verify it is current (CI)

The zip is written deterministically (sorted entries, a fixed timestamp, fixed
compression) so --check can byte-compare it, the same contract as the bundle and
plugin-mirror guards. Run build_plugin.py first if the mirror is stale; this reads
from it.
"""
import argparse
import sys
import zipfile
from pathlib import Path
from safeio import atomic_write_bytes

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "zero-slop"
OUT = ROOT / "dist" / "zero-slop.zip"
FIXED_DATE = (1980, 1, 1, 0, 0, 0)  # zip epoch; keeps the archive reproducible
EXCLUDE = {"__pycache__", ".DS_Store"}


def _files():
    return sorted(
        p for p in SKILL_DIR.rglob("*")
        if p.is_file() and not p.is_symlink()
        and not any(part in EXCLUDE for part in p.parts))


def _symlinks():
    return sorted(path for path in SKILL_DIR.rglob("*") if path.is_symlink())


def build_bytes():
    """Return the deterministic zip as bytes (folder 'zero-slop/...' at the root)."""
    import io
    if not SKILL_DIR.is_dir() or SKILL_DIR.is_symlink() or _symlinks():
        raise ValueError("skill source is missing or contains symlinks")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in _files():
            arc = "zero-slop/" + f.relative_to(SKILL_DIR).as_posix()
            info = zipfile.ZipInfo(arc, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, f.read_bytes())
    return buf.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not SKILL_DIR.is_dir() or SKILL_DIR.is_symlink():
        print("skills/zero-slop/ is missing — run: python3 scripts/build_plugin.py")
        return 1
    links = _symlinks()
    if links:
        print(f"skill package refuses symlinked input: {links[0]}")
        return 1
    files = _files()
    skill_files = [path for path in files if path.name == "SKILL.md"]
    if (len(skill_files) != 1 or skill_files[0] != SKILL_DIR / "SKILL.md"):
        print(f"skill package needs exactly one SKILL.md, found {len(skill_files)}")
        return 1
    try:
        data = build_bytes()
    except (OSError, ValueError) as exc:
        print(f"cannot build skill package: {exc}", file=sys.stderr)
        return 1
    check = args.check
    if check:
        if not OUT.exists() or OUT.read_bytes() != data:
            print("dist/zero-slop.zip is out of date — run: python3 scripts/build_skill_zip.py")
            return 1
        print("dist/zero-slop.zip is current")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        atomic_write_bytes(OUT, data)
    except OSError as exc:
        print(f"cannot write {OUT}: {exc}", file=sys.stderr)
        return 1
    n = len(files)
    print(f"wrote {OUT.relative_to(ROOT)} ({n} files, one skill, {len(data):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
