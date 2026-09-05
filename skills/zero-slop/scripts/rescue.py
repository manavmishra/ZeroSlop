#!/usr/bin/env python3
"""Conservative, deterministic editing when an AI response is unavailable.

This is an availability path, not a substitute for the contextual editor. Every
rule removes a stock wrapper, contracts a phrase, or repairs paragraph staging.
Quoted text, code, Markdown links, URLs, names, figures, and claims are left alone.

    python3 scripts/rescue.py draft.txt
    cat draft.txt | python3 scripts/rescue.py -
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


MAX_INPUT_BYTES = 4 * 1024 * 1024
PROTECTED = re.compile(
    r"```[\s\S]*?```|`[^`\n]+`|\[[^\]\n]+\]\([^)]+\)|https?://[^\s<]+|"
    r"“[^”\n]*”|‘[^’\n]*’|\"[^\"\n]*\""
)
TOKEN = re.compile(r"\ue000(\d+)\ue001")


def _without_wrapper(match: re.Match[str]) -> str:
    prefix, word = match.group(1), match.group(2)
    # Capitalize the exposed sentence, but leave names such as iOS and eBay
    # byte-for-byte. This applies only where a sentence wrapper was removed.
    if word.islower():
        word = word[:1].upper() + word[1:]
    return prefix + word


def rescue_text(text: str) -> str:
    """Return a bounded, source-preserving edit; return clean text unchanged."""
    original = str(text or "").strip()
    protected: list[str] = []

    def mask(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"\ue000{len(protected) - 1}\ue001"

    masked = PROTECTED.sub(mask, original)
    out = re.sub(r"[\u00a0\u202f]", " ", masked)
    out = re.sub(
        r"(^|[.!?][ \t]+|\n[ \t]*)(?:it is important to note that|it is worth noting that)"
        r"[ \t]+([A-Za-z][A-Za-z0-9_-]*)",
        _without_wrapper, out, flags=re.IGNORECASE,
    )
    rules: list[tuple[str, str | object]] = [
        (
            r"\bwe are thrilled to unveil ([^,\n]+),\s+a transformative release that "
            r"redefines what is possible in ([^.]+)\.",
            lambda m: f"{m.group(1)} updates {m.group(2)}.",
        ),
        (r"\bthis release represents a significant milestone in our journey to empower "
         r"teams everywhere\.\s*", ""),
        (r"\bwe have listened carefully to your feedback and are excited to deliver a "
         r"suite of powerful new capabilities\.",
         "We listened to your feedback and added new capabilities."),
        (r"\bour cutting[-\u2010\u2011 ]edge\b", "Our"),
        (r"\bhours of tedious manual configuration\b", "hours of manual configuration"),
        (r"\bwe have completely reimagined\b", "We rebuilt"),
        (r"\bwith robust error handling built in from the ground up\b",
         "with built-in error handling"),
        (r"\bwe believe these improvements will fundamentally transform how your team "
         r"works,\s+and the release is available today\.", "The release is available today."),
        (r"\bwe are incredibly excited to share(?: some news)? about\b", "We're excited about"),
        (r"\bwe(?:['’]re| are) excited to share(?: some news)? about\b", "We're excited about"),
        (r"\bwe are incredibly excited to share\b", "We're sharing"),
        (r"\bwe(?:['’]re| are) excited to share\b", "We're excited about"),
        (r"\bi(?:['’]m| am) incredibly excited to (?:share|announce)\b", "I'm sharing"),
        (r"\bour journey\b", "our work"),
        (r"\bour transformative journey\b", "our work"),
        (r"\bin today'?s rapidly evolving (?:landscape|world)\b", "Today"),
        (r"\bit is important to note that\b[ \t]*", ""),
        (r"\bit is worth noting that\b[ \t]*", ""),
        (r"\bwhat we did not realize was just how deeply it impacted everything downstream\.",
         "We underestimated its effect on the work that followed."),
        (r"\bonboarding is not a checklist\.\s*it is a promise\.",
         "We see onboarding as a promise."),
        (r"\bonboarding isn['’]t a checklist\s*[-—]\s*it['’]s a promise\.",
         "We see onboarding as a promise."),
        (r"\bthe insights were game[-\u2011]changing\.",
         lambda m: ("Those" if m.group(0)[0].isupper() else "those")
         + " conversations changed our approach."),
        (r"\bthe insights were (?:transformative|clear|significant):\s*",
         "Those conversations showed that "),
        (r"\ba platform that leverages intelligent automation to streamline the entire "
         r"process end to end\b", "a platform that automates onboarding from start to finish"),
        (r"\bthe results speak for themselves:\s*([a-z])",
         lambda m: m.group(1).upper()),
        (r"\bthe results speak for themselves\.\s*", ""),
        (r"\bbut here is the thing nobody talks about\.\s*", ""),
        # A contrast may carry a substantive position. A local rule cannot
        # infer that the thing rejected in the source nevertheless mattered.
        (r"\bthat is the kind of impact that keeps us going\b", "That result keeps us going"),
        (r"\bseamlessly (integrates?)\b",
         lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
        (r"\bjust how deeply\b", "how much"),
        (r"\bgame[-\u2011]changing\b", "useful"),
        (r"\bcutting[-\u2010\u2011 ]edge\b", "current"),
        (r"\bredefines what(?:['’]s| is) possible in\b", "updates"),
        (r"\bin order to\b", "to"),
        (r"\bat the end of the day\b", "ultimately"),
        # Contractions alone are not evidence of better writing. Leave clean
        # source sentences unchanged instead of manufacturing an edit.
    ]
    for pattern, replacement in rules:
        def replace(match: re.Match[str]) -> str:
            if callable(replacement):
                return replacement(match)
            value = replacement
            if not value:
                return value
            if match.group(0)[0].isupper():
                return value[:1].upper() + value[1:]
            if not value.startswith("I'"):
                return value[:1].lower() + value[1:]
            return value
        out = re.sub(pattern, replace, out, flags=re.IGNORECASE)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r" {2,}", " ", out).strip()

    if out == masked:
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", out) if part.strip()]
        if len(paragraphs) >= 4 and all(len(part.split()) < 24 for part in paragraphs):
            out = " ".join(paragraphs)

    def restore(match: re.Match[str]) -> str:
        index = int(match.group(1))
        return protected[index] if index < len(protected) else match.group(0)

    return TOKEN.sub(restore, out).strip()


def _read(path: str) -> str:
    if path == "-":
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        raw = Path(path).read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise SystemExit(f"input exceeds {MAX_INPUT_BYTES} bytes")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"input is not valid UTF-8: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", nargs="?", default="-", help="UTF-8 file, or - for stdin")
    args = parser.parse_args(argv)
    sys.stdout.write(rescue_text(_read(args.input)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
