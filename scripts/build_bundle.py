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
import argparse
import sys
from pathlib import Path
from safeio import atomic_write_text

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
    "references/readalong.md",
    "references/copy-desk.md",
    "references/eval.md",
    "references/fresh-eyes.md",
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

The local writing check needs a shell and is not included here. With Code
Interpreter enabled you can also upload scripts/slopscore.py from the repo to
get the numbers; without it, use the reference lists and editorial checks below.

GENERATED FILE — do not edit. Run scripts/build_bundle.py after changing
SKILL.md or anything in references/.

Source: https://github.com/manavmishra/ZeroSlop   MIT
-->

"""


def build():
    out = [HEADER]
    for rel in PARTS:
        p = ROOT / rel
        if not p.is_file() or p.is_symlink():
            print(f"missing or unsafe source: {rel}", file=sys.stderr)
            return None
        try:
            text = p.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"cannot read source {rel}: {exc}", file=sys.stderr)
            return None
        out.append(f"\n\n{RULE}\n# FILE: {rel}\n{RULE}\n\n")
        out.append(text.rstrip() + "\n")
    return "".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = build()
    if text is None:
        return 1
    check = args.check
    current = OUT.read_text() if OUT.exists() else ""
    if check:
        if current != text:
            print("dist bundle is out of date — run: python3 scripts/build_bundle.py")
            return 1
        print("dist bundle is current")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        atomic_write_text(OUT, text)
    except OSError as exc:
        print(f"cannot write {OUT}: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {OUT.relative_to(ROOT)} "
          f"({len(text.splitlines()):,} lines, {len(text):,} chars, "
          f"{len(PARTS)} sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
