#!/usr/bin/env python3
"""build_bundle — regenerate dist/zero-slop-single-file.md from the sources.

ChatGPT Projects, Custom GPT Knowledge and Codex all want one pasteable file
rather than a repository, so the skill and its reference documents are
concatenated into a single artifact. Maintaining that by hand does not work:
the bundle silently kept describing a 72-term lexicon for weeks after the real
figure became 54, because nothing regenerated it and nothing checked.

    python3 scripts/build_bundle.py           # rebuild
    python3 scripts/build_bundle.py --check   # fail if stale (CI)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "zero-slop-single-file.md"
# SKILL.md first — it is the runtime contract; the references it points to follow
# in the order the loop consults them.
PARTS = [
    "SKILL.md",
    "references/tells.md",
    "references/rewrite-moves.md",
    "references/platforms.md",
    "references/overcorrection.md",
    "references/evidence.md",
]
RULE = "=" * 72

HEADER = """<!--
Zero Slop — single-file bundle for ChatGPT, Codex, and any assistant that
takes pasted instructions or an uploaded knowledge file.

HOW TO USE
  ChatGPT / ChatGPT at Work : Project → Instructions → paste this file.
                              Or Custom GPT → Knowledge → upload this file.
  Codex                     : save as AGENTS.md in your project.
  Anything else             : paste it. It is self-contained.

The statistical scorer needs a shell and is not included here. With Code
Interpreter enabled you can also upload scripts/slopscore.py from the repo to
get the numbers; without it, the reference lists below are the gate.

GENERATED FILE — do not edit. Run scripts/build_bundle.py after changing
SKILL.md or anything in references/.

Source: https://github.com/manavmishra/ZeroSlop   MIT
-->

"""


def build():
    out = [HEADER]
    for rel in PARTS:
        p = ROOT / rel
        if not p.exists():
            print(f"missing source: {rel}", file=sys.stderr)
            return None
        out.append(f"\n\n{RULE}\n# FILE: {rel}\n{RULE}\n\n")
        out.append(p.read_text().rstrip() + "\n")
    return "".join(out)


def main():
    text = build()
    if text is None:
        return 1
    check = "--check" in sys.argv
    current = OUT.read_text() if OUT.exists() else ""
    if check:
        if current != text:
            print("dist bundle is out of date — run: python3 scripts/build_bundle.py")
            return 1
        print("dist bundle is current")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)} "
          f"({len(text.splitlines()):,} lines, {len(text):,} chars, "
          f"{len(PARTS)} sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
