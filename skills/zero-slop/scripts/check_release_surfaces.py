#!/usr/bin/env python3
"""Every published surface must advertise the version this repo ships.

The in-repo surfaces already have a unit test: plugin manifests, SKILL.md, the
README badge, the one-pager, the website literal. Nothing watched the surfaces
that live outside the tree, and that is exactly where the drift happened --
v2.8.2 and v2.8.3 were tagged and never released, so
releases/latest/download/zero-slop.zip, which the README hands Claude.ai users,
served v2.8.1 for two releases.

Checked here:
  the newest GitHub release tag
  the skill version inside that release's zero-slop.zip
  the version published to npm

Network is optional. Unreachable is reported and skipped, never failed: this
runs beside a test suite that must work offline, and a check that cries wolf
on a dropped connection gets ignored. Only a real disagreement exits non-zero.
"""
import io
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "manavmishra/ZeroSlop"
TIMEOUT = 20


def fetch(url, *, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "zero-slop-release-check"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read() if binary else r.read().decode()
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                raise
        except Exception:
            if attempt == 2:
                raise
    raise RuntimeError("unreachable")


def main() -> int:
    shipped = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    print(f"this repo ships           {shipped}")
    problems, skipped = [], []

    try:
        rel = json.loads(fetch(f"https://api.github.com/repos/{REPO}/releases/latest"))
        tag = rel.get("tag_name", "")
        print(f"newest GitHub release     {tag}")
        if tag.lstrip("v") != shipped:
            problems.append(f"the newest GitHub release is {tag}, not v{shipped}. "
                            f"Tag pushed without a release? release-on-tag.yml should have created it.")
    except Exception as e:
        skipped.append(f"GitHub releases ({e})")

    try:
        blob = fetch(f"https://github.com/{REPO}/releases/latest/download/zero-slop.zip", binary=True)
        z = zipfile.ZipFile(io.BytesIO(blob))
        names = [n for n in z.namelist() if n.endswith("SKILL.md")]
        inside = re.search(r'version:\s*"([0-9.]+)"', z.read(names[0]).decode()).group(1)
        print(f"inside that release's ZIP {inside}")
        if inside != shipped:
            problems.append(f"releases/latest/download/zero-slop.zip contains {inside}, not {shipped}. "
                            f"This is the download the README gives Claude.ai users.")
    except Exception as e:
        skipped.append(f"release ZIP ({e})")

    try:
        meta = json.loads(fetch("https://registry.npmjs.org/zero-slop/latest"))
        print(f"published to npm          {meta.get('version')}")
        if meta.get("version") != shipped:
            problems.append(f"npm publishes {meta.get('version')}, not {shipped}.")
    except Exception as e:
        skipped.append(f"npm ({e})")

    for s in skipped:
        print(f"skipped: {s}")
    if problems:
        print()
        for p in problems:
            print(f"DRIFT: {p}")
        return 1
    if not skipped:
        print("\nEvery published surface advertises the version this repo ships.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
