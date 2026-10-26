#!/usr/bin/env python3
"""Offline, conservative copy-artifact cleanup; not a watermark detector."""
import argparse
import hashlib
import json
import os
import re
import stat
import sys

POLICY_VERSION = "2026-10-26.1"
REMOVABLE = re.compile("[\u200b\u2060\ufeff]")
WORDS = frozenset("a an and are clear draft hello in is of text the this to world writing".split())
PROTECTED = re.compile(r'''^ {4}|^\t|[`"'<>$=\\:|]|https?:|www\.|@|\]\(|\b(?:identifier|variable|function|path|command|token|password|code|regex|formula|equation)\b|\b\w+[./_]\w+\b''', re.I)


def _validate(text):
    if not isinstance(text, str):
        raise TypeError("Text must be a string.")
    if len(text.encode("utf-16-le", errors="surrogatepass")) // 2 > 200000:
        raise ValueError("Text hygiene input exceeds 200000 UTF-16 units.")


def clean_text_hygiene(text):
    _validate(text)
    edits, offset, fence, frontmatter = [], 0, None, False
    markup = "<" in text or ">" in text
    parts = text.split("\n")
    for line_index, part in enumerate(parts):
        line = part + ("\n" if line_index < len(parts) - 1 else "")
        if offset == 0 and re.fullmatch("\ufeff?---\\s*", line):
            frontmatter = True
            offset += len(line)
            continue
        if frontmatter:
            if re.fullmatch(r"(?:---|\.\.\.)\s*", line):
                frontmatter = False
            offset += len(line)
            continue
        marker = re.match(r"\s*(`{3,}|~{3,})", line)
        if marker:
            char = marker[1][0]
            if not fence:
                fence = (char, len(marker[1]))
            elif fence[0] == char and len(marker[1]) >= fence[1] and re.fullmatch(r"\s*(?:`+|~+)\s*", line):
                fence = None
            offset += len(line)
            continue
        plain = REMOVABLE.sub("", line)
        protected = markup or fence or re.search(r"[^\x09\x0a\x0d\x20-\x7e]", plain) or PROTECTED.search(plain)
        if not protected and len(re.findall(r"[A-Za-z]+", plain)) >= 2:
            for match in re.finditer("[A-Za-z\u200b\u2060\ufeff]+", line):
                word = match[0]
                if REMOVABLE.sub("", word).lower() not in WORDS:
                    continue
                for index in range(1, len(word) - 1):
                    if word[index] in "\u200b\u2060\ufeff" and re.fullmatch("[A-Za-z]", word[index - 1]) and re.fullmatch("[A-Za-z]", word[index + 1]):
                        start = offset + match.start() + index
                        edits.append({"start": start, "end": start + 1, "original": word[index], "replacement": "", "reason": "embedded_ascii_copy_artifact"})
        offset += len(line)
    chunks, cursor = [], 0
    for edit in edits:
        chunks.append(text[cursor:edit["start"]])
        cursor = edit["end"]
    chunks.append(text[cursor:])
    cleaned = "".join(chunks)
    digest = hashlib.sha256(cleaned.encode("utf-8", errors="surrogatepass")).hexdigest()
    for index, edit in enumerate(edits):
        edit.update(outputStart=edit["start"] - index, outputBinding=digest)
    return {"text": cleaned, "edits": edits, "status": "cleaned" if edits else "unchanged", "policyVersion": POLICY_VERSION,
            "offsetUnit": "codepoint", "statisticalWatermark": {"status": "not_verified", "reason": "matching_detector_unavailable"}}


def inspect_text_hygiene(text):
    result = clean_text_hygiene(text)
    actionable = {edit["start"] for edit in result["edits"]}
    findings = []
    for index, char in enumerate(text):
        cp = ord(char)
        if cp in (0xad, 0xfeff) or 0x200b <= cp <= 0x200f or 0x202a <= cp <= 0x202e or 0x2060 <= cp <= 0x2069 or 0xfe00 <= cp <= 0xfe0f or 0xe0000 <= cp <= 0xe01ef:
            findings.append({"start": index, "codePoint": f"U+{cp:04X}", "disposition": "removable" if index in actionable else "preserved"})
    return dict(result, text=text, findings=findings, status="inspected")


def reverse_text_hygiene(text, edits):
    _validate(text)
    if not isinstance(edits, list) or len(edits) > 200000:
        raise ValueError("Edits must be a bounded array.")
    digest = hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()
    chunks, cursor, previous = [], 0, -1
    for index, edit in enumerate(edits):
        if not isinstance(edit, dict):
            raise ValueError("Cleanup plan does not match this text.")
        start = edit.get("start")
        output_start = edit.get("outputStart")
        if (type(start) is not int or not 1 <= start <= len(text) + len(edits)
                or type(output_start) is not int or not 0 <= output_start <= len(text)
                or start <= previous or type(edit.get("end")) is not int
                or edit["end"] != start + 1
                or edit.get("original") not in ("\u200b", "\u2060", "\ufeff")
                or edit.get("replacement") != "" or edit.get("outputBinding") != digest
                or output_start != start - index):
            raise ValueError("Cleanup plan does not match this text.")
        previous = start
        chunks.extend((text[cursor:output_start], edit["original"]))
        cursor = output_start
    chunks.append(text[cursor:])
    return "".join(chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="UTF-8 file or - for stdin")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    maximum = 128 * 1024
    if args.path == "-":
        payload = sys.stdin.buffer.read(maximum + 1)
    else:
        descriptor = os.open(args.path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("Provide a regular UTF-8 file.")
            payload = source.read(maximum + 1)
    if len(payload) > maximum:
        raise ValueError("Input exceeds 128 KiB.")
    text = payload.decode("utf-8", errors="strict")
    result = inspect_text_hygiene(text) if args.inspect else clean_text_hygiene(text)
    print(json.dumps(result, ensure_ascii=True) if args.json else result["text"], end="\n" if args.json else "")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError):
        print("Text cleanup failed: provide bounded, valid UTF-8 input.", file=sys.stderr)
        raise SystemExit(2)
