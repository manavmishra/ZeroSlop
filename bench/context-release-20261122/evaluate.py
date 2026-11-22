"""Replay independent synthetic drafts against the fixed local fallback.

This checks exact source spans and clean controls. It makes no model calls and
does not certify semantic equivalence or human-perceived voice quality.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from rescue import rescue_text

folder = Path(__file__).resolve().parent
raw = (folder / "drafts.json").read_bytes()
rows = []
for row in json.loads(raw):
    edited = rescue_text(row["source"])
    rows.append({
        **row,
        "edited": edited,
        "changed": edited != row["source"],
        "protected_spans_preserved": all(span in edited for span in row["protected_spans"]),
        "idempotent": rescue_text(edited) == edited,
        "clean_control_unchanged": edited == row["source"] if row["expected_action"] == "keep" else None,
    })

print(json.dumps({
    "scope": "Synthetic local-fallback replay; no model rewrite or human voice evaluation",
    "drafts_sha256": hashlib.sha256(raw).hexdigest(),
    "runtime_sha256": hashlib.sha256((ROOT / "scripts/rescue.py").read_bytes()).hexdigest(),
    "drafts": len(rows),
    "protected_span_failures": sum(not row["protected_spans_preserved"] for row in rows),
    "idempotence_failures": sum(not row["idempotent"] for row in rows),
    "clean_controls": sum(row["expected_action"] == "keep" for row in rows),
    "clean_control_changes": sum(row["clean_control_unchanged"] is False for row in rows),
    "results": rows,
}, indent=2, ensure_ascii=False))
