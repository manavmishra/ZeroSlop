#!/usr/bin/env python3
"""Build the versioned 72-item blind quality panel from committed rewrites."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SEARCH = ROOT / "bench" / "search-corpus"
PROTOCOL = HERE / "protocol.md"
MANIFEST = HERE / "manifest.json"
PACKET = HERE / "blind-packet.json"
sys.path.insert(0, str(ROOT / "scripts"))
from safeio import atomic_write_text  # noqa: E402
from common import load_manifest, text_sha256  # noqa: E402

SOURCE_SPLITS = {
    "linkedin-lessons-01": "dev", "linkedin-contrarian-02": "test",
    "x-agents-01": "dev", "x-habit-02": "test",
    "email-outreach-01": "dev", "email-launch-02": "test",
    "blog-landscape-01": "dev", "blog-guide-02": "test",
    "newsletter-productivity-01": "dev", "newsletter-edition-02": "test",
    "research-framework-01": "dev", "research-approach-02": "test",
}
METHOD_FILES = {
    "zero-slop": "zero-slop.json",
    "humanizer": "humanizer.json",
    "no-ai-slop": "no-ai-slop.json",
    "de-slop": "de-slop.json",
    "stop-slop": "stop-slop.json",
}
SALT = "zero-slop-blind-quality-panel-v1"


def compute():
    corpus = {row["id"]: row for row in json.loads((SEARCH / "corpus.json").read_text())}
    if not set(SOURCE_SPLITS).issubset(corpus):
        raise ValueError("search corpus no longer contains every quality-panel source")
    outputs = {method: json.loads((SEARCH / "outputs" / filename).read_text())
               for method, filename in METHOD_FILES.items()}
    rows = []
    for source_id, split in SOURCE_SPLITS.items():
        source = corpus[source_id]
        variants = {"original": source["text"],
                    **{method: data[source_id] for method, data in outputs.items()}}
        for method, text in variants.items():
            blind_key = hashlib.sha256(
                f"{SALT}\0{source_id}\0{method}".encode()).hexdigest()
            rows.append({"blind_key": blind_key, "source_id": source_id,
                         "split": split, "genre": source["genre"],
                         "method": method, "text": text,
                         "text_sha256": text_sha256(text)})
    rows.sort(key=lambda row: row["blind_key"])
    for row in rows:
        row.pop("blind_key")
    for index, row in enumerate(rows, 1):
        row["id"] = f"q{index:03d}"
    manifest = {
        "schema": 1,
        "corpus_kind": "blind_slop_quality_panel",
        "label_protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "items": rows,
    }
    load_manifest_data = manifest
    # Validate through the same strict file contract by using the equivalent
    # invariants here before any output is committed.
    if len(load_manifest_data["items"]) != 72:
        raise ValueError("quality panel must contain exactly 72 items")
    packet = {
        "schema": 1,
        "protocol_sha256": manifest["label_protocol_sha256"],
        "items": [{"id": row["id"], "text": row["text"]} for row in rows],
    }
    return manifest, packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        manifest, packet = compute()
        if args.write:
            atomic_write_text(MANIFEST, json.dumps(manifest, indent=1) + "\n")
            atomic_write_text(PACKET, json.dumps(packet, indent=1) + "\n")
            load_manifest(MANIFEST)
        else:
            if json.loads(MANIFEST.read_text()) != manifest:
                raise ValueError("manifest.json is stale")
            if json.loads(PACKET.read_text()) != packet:
                raise ValueError("blind-packet.json is stale")
            load_manifest(MANIFEST)
        print("quality panel: 72 blind items from 12 source drafts")
        return 0
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"quality panel: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
