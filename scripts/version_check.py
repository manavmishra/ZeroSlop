#!/usr/bin/env python3
"""version_check — is this copy of the skill the latest release?

The skill runs step 0 of its loop through this so a stale install tells on itself
and points at the one-line update, instead of silently de-slopping with an old tell
list. It compares the version in SKILL.md against the latest GitHub release and
prints what to run if a newer one exists.

    python3 scripts/version_check.py            # human-readable, always prints
    python3 scripts/version_check.py --quiet    # print only if an update exists (step 0)
    python3 scripts/version_check.py --json      # machine-readable

Two promises this keeps. It sends **only a version query** — never a draft or any
word from it — so the check does not expose writing. And
it fails open: no network, a timeout, any error, and it exits 0 with a quiet note,
because a de-slop run must never break over a missing changelog. Set
`ZS_NO_UPDATE_CHECK=1` to skip it entirely.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASES = "https://api.github.com/repos/manavmishra/ZeroSlop/releases/latest"
TIMEOUT = 2.5


def local_version():
    """The version this copy declares, from SKILL.md's frontmatter."""
    text = (ROOT / "SKILL.md").read_text()
    m = re.search(r'^\s*version:\s*"?([\d.]+)"?', text, re.M)
    return m.group(1) if m else None


def _tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or ""))


def latest_version():
    """The newest published release tag, or None if it cannot be reached.

    Sends one GET to the public releases API and reads the tag. No auth, no body,
    nothing about the draft — just 'what is the latest tag'.
    """
    if os.getenv("ZS_NO_UPDATE_CHECK"):
        return None
    try:
        req = urllib.request.Request(RELEASES, headers={"Accept": "application/vnd.github+json",
                                                        "User-Agent": "zero-slop-version-check"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            tag = json.load(r).get("tag_name", "")
        return tag.lstrip("vV") or None
    except Exception:
        return None  # fail open: offline, rate-limited, or no release yet


def install_hint():
    """The right update command for how this copy was installed."""
    if (ROOT / ".git").exists():
        return "git -C %s pull" % ROOT
    return "npx skills add manavmishra/ZeroSlop --global   # re-run to update"


def check():
    local = local_version()
    latest = latest_version()
    behind = bool(local and latest and _tuple(latest) > _tuple(local))
    return {"local": local, "latest": latest, "update_available": behind,
            "command": install_hint() if behind else None,
            "checked": latest is not None}


def main():
    r = check()
    if "--json" in sys.argv:
        print(json.dumps(r))
        return 0
    if r["update_available"]:
        print(f"Zero Slop {r['latest']} is out — you have {r['local']}. Update:\n  {r['command']}")
    elif "--quiet" not in sys.argv:
        if not r["checked"]:
            print(f"Zero Slop {r['local']} — could not check for updates (offline or rate-limited).")
        else:
            print(f"Zero Slop {r['local']} is the latest release.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
