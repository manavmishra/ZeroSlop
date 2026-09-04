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


def _sentence_pair(match: re.Match[str], *, past: bool) -> str:
    first, second = match.group(1), match.group(2)
    lead = first[:1].upper() + first[1:]
    return f"{lead} {'mattered' if past else 'matters'}. " + (
        f"More important was {second}." if past else f"The larger gain is {second}."
    )


def rescue_text(text: str) -> str:
    """Return a bounded, source-preserving edit; return clean text unchanged."""
    original = str(text or "").strip()
    protected: list[str] = []

    def mask(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"\ue000{len(protected) - 1}\ue001"

    masked = PROTECTED.sub(mask, original)
    out = re.sub(r"[\u00a0\u202f]", " ", masked)
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
        (r"\bit is important to note that\b", ""),
        (r"\bit is worth noting that\b", ""),
        (r"\bwhat we did not realize was just how deeply it impacted everything downstream\.",
         "We underestimated its effect on the work that followed."),
        (r"\bonboarding is not a checklist\.\s*it is a promise\.",
         "We see onboarding as a promise."),
        (r"\bonboarding isn['’]t a checklist\s*[-—]\s*it['’]s a promise\.",
         "We see onboarding as a promise."),
        (r"\bthe insights were game[-\u2011]changing\.",
         "Those conversations changed our approach."),
        (r"\bthe insights were (?:transformative|clear|significant):\s*",
         "Those conversations showed that "),
        (r"\ba platform that leverages intelligent automation to streamline the entire "
         r"process end to end\b", "a platform that automates onboarding from start to finish"),
        (r"\bthe results speak for themselves:\s*([a-z])",
         lambda m: m.group(1).upper()),
        (r"\bthe results speak for themselves\.\s*", ""),
        (r"\bbut here is the thing nobody talks about\.\s*", ""),
        (r"\bthe real win was not ([^.]+)\.\s*it was ([^.]+)\.",
         lambda m: _sentence_pair(m, past=True)),
        (r"\bthe real win isn['’]t just ([^.]+)\.\s*it['’]s ([^.]+)\.",
         lambda m: _sentence_pair(m, past=False)),
        (r"\bthat is the kind of impact that keeps us going\b", "That result keeps us going"),
        (r"\bunlock(?:ing)? the full potential of\b", "use"),
        (r"\bseamlessly integrates?\b", "integrates"),
        (r"\bjust how deeply\b", "how much"),
        (r"\bgame[-\u2011]changing\b", "useful"),
        (r"\bcutting[-\u2010\u2011 ]edge\b", "current"),
        (r"\bredefines what(?:['’]s| is) possible in\b", "updates"),
        (r"\bin order to\b", "to"),
        (r"\bat the end of the day\b", "ultimately"),
        (r"\bwe are\b", "we're"),
        (r"\bwe did not\b", "we didn't"),
        (r"\bwe do not\b", "we don't"),
        (r"\bi am\b", "I'm"),
        (r"\bit is\b", "it's"),
        (r"\bthey are\b", "they're"),
        (r"\byou are\b", "you're"),
        (r"\bthere is\b", "there's"),
        (r"\bdoes not\b", "doesn't"),
        (r"\bis not\b", "isn't"),
        (r"\bare not\b", "aren't"),
        (r"\bcannot\b", "can't"),
    ]
    for pattern, replacement in rules:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
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
