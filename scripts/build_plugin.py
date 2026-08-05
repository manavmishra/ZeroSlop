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
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "skills" / "zero-slop"
# What constitutes the skill. Docs, benchmarks and manifests stay at the root:
# a plugin payload should carry the runtime, not the marketing.
ITEMS = ["SKILL.md", "references", "scripts", "data"]
# Never mirror: personal voice profiles, caches, or this script's own output.
EXCLUDE = {"voices", "__pycache__", "build_plugin.py"}


def wanted(src: Path):
    return [p for p in src.rglob("*")
            if p.is_file() and not any(part in EXCLUDE for part in p.parts)]


def build(check=False):
    stale, copied = [], 0
    DEST.mkdir(parents=True, exist_ok=True)
    live = set()
    for item in ITEMS:
        src = ROOT / item
        if not src.exists():
            continue
        if src.is_file():
            pairs = [(src, DEST / item)]
        else:
            pairs = [(p, DEST / p.relative_to(ROOT)) for p in wanted(src)]
        for s, d in pairs:
            live.add(d)
            if check:
                if not d.exists() or not filecmp.cmp(s, d, shallow=False):
                    stale.append(str(d.relative_to(ROOT)))
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
                copied += 1
    # anything in the mirror that no longer exists at the root is stale
    if DEST.exists():
        for p in DEST.rglob("*"):
            if p.is_file() and p not in live:
                if check:
                    stale.append(str(p.relative_to(ROOT)) + " (orphan)")
                else:
                    p.unlink()
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


def _zip(check):
    """Keep the single-skill claude.ai zip in step with the mirror."""
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_skill_zip.py")]
                       + (["--check"] if check else []), capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    return r.returncode


if __name__ == "__main__":
    check = "--check" in sys.argv
    rc = build(check=check)
    rc = _zip(check) or rc
    sys.exit(rc)
