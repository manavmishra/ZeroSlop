#!/usr/bin/env python3
"""build_plugin — mirror the root skill into skills/zero-slop/ for plugin installs.

Two install conventions want two different layouts:

  * the skills CLI, a direct `git clone`, and claude.ai zip uploads read the
    skill from the repository root (`SKILL.md` beside `references/`);
  * the Claude Code / Cowork plugin system reads `skills/<name>/SKILL.md`,
    because one plugin may ship several skills.

Rather than maintain two copies by hand — which drifts the moment someone
edits one and forgets the other — the root is the single source of truth and
this script regenerates the nested copy. CI runs it with --check so a pull
request that edits the root without rebuilding fails loudly.

    python3 scripts/build_plugin.py            # rebuild the mirror
    python3 scripts/build_plugin.py --check    # verify it is current (CI)
"""
import argparse
import filecmp
import stat
import sys
from pathlib import Path
from safeio import atomic_write_bytes, is_within

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "skills" / "zero-slop"
# What constitutes the skill. Docs, benchmarks and manifests stay at the root:
# a plugin payload should carry the runtime, not the marketing.
ITEMS = ["SKILL.md", "references", "scripts", "data"]
# Never mirror personal state, caches, or maintainer/build utilities. The plugin
# carries only files the installed skill can execute at runtime.
EXCLUDE = {
    "voices", "__pycache__", "build_plugin.py", "build_bundle.py",
    "build_onepager_pdf.py", "build_skill_zip.py", "check_svg.py",
    # A maintainer check against GitHub and npm, not something an installed
    # skill should carry or run.
    "check_distribution_manifests.py", "check_release_version.py",
    "check_release_surfaces.py",
    "contextual.py", "contextual-signals.md", ".DS_Store",
    "make-readme-gif.mjs",
}


def wanted(src: Path):
    return [p for p in src.rglob("*")
            if p.is_file() and not p.is_symlink()
            and not any(part in EXCLUDE for part in p.parts)]


def build(check=False):
    stale, copied = [], 0
    if DEST.is_symlink() or not is_within(DEST, ROOT):
        print(f"refusing plugin destination outside the repository: {DEST}")
        return 1
    missing = []
    for item in ITEMS:
        source = ROOT / item
        expected = source.is_file() if item == "SKILL.md" else source.is_dir()
        if not expected or source.is_symlink():
            missing.append(item)
    if missing:
        print("plugin source is incomplete or unsafe: " + ", ".join(missing))
        return 1
    DEST.mkdir(parents=True, exist_ok=True)
    destination_links = sorted(
        (path for path in DEST.rglob("*") if path.is_symlink()),
        key=lambda path: len(path.parts), reverse=True,
    )
    if destination_links and check:
        stale.extend(str(path.relative_to(ROOT)) + " (symlink)"
                     for path in destination_links)
    elif destination_links:
        for path in destination_links:
            path.unlink()
    live = set()
    for item in ITEMS:
        src = ROOT / item
        if src.is_file():
            pairs = [(src, DEST / item)]
        else:
            links = [path for path in src.rglob("*") if path.is_symlink()]
            if links:
                print(f"refusing symlinked plugin source: {links[0]}")
                return 1
            pairs = [(p, DEST / p.relative_to(ROOT)) for p in wanted(src)]
        for s, d in pairs:
            live.add(d)
            if check:
                unsafe_parent = any(parent.is_symlink()
                                    for parent in d.parents if parent != DEST.parent)
                if (d.is_symlink() or unsafe_parent or not d.exists()
                        or not filecmp.cmp(s, d, shallow=False)):
                    stale.append(str(d.relative_to(ROOT)))
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_bytes(d, s.read_bytes(),
                                   mode=stat.S_IMODE(s.stat().st_mode))
                copied += 1
    # anything in the mirror that no longer exists at the root is stale
    if DEST.exists():
        for p in DEST.rglob("*"):
            if (p.is_file() or p.is_symlink()) and p not in live:
                if check:
                    stale.append(str(p.relative_to(ROOT)) + " (orphan)")
                else:
                    p.unlink()
        if not check:
            # Remove directories left empty when a source subtree is retired.
            # Deepest-first order keeps the mirror free of obsolete names.
            directories = sorted(
                (p for p in DEST.rglob("*") if p.is_dir() and not p.is_symlink()),
                key=lambda p: len(p.parts),
                reverse=True,
            )
            for directory in directories:
                if not any(directory.iterdir()):
                    directory.rmdir()
    if check:
        if stale:
            print("plugin mirror is out of date:")
            for s in stale:
                print("  -", s)
            print("\nrun: python3 scripts/build_plugin.py")
            return 1
        print("plugin mirror is current")
        return 0
    print(f"mirrored {copied} files into skills/zero-slop/")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return build(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
