#!/usr/bin/env python3
"""Validate the corpus admission registry and its no-false-accuracy contract."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "bench" / "corpus-registry.json"
TIERS = {"release_gate", "release_research", "candidate_research",
         "restricted_research", "discovery_only"}
STATUSES = {"measured", "not_run", "not_run_for_slop_accuracy",
            "indirectly_used_via_beemo", "reviewed"}
FIELDS = {"id", "name", "url", "license", "label_semantics", "intended_use",
          "tier", "access", "status", "result", "source_pin"}
ID = re.compile(r"[a-z0-9][a-z0-9-]{1,63}\Z")


def validate(path=REGISTRY):
    data = json.loads(Path(path).read_text())
    if (not isinstance(data, dict) or set(data) != {"schema", "policy", "datasets"}
            or data.get("schema") != 1 or not isinstance(data.get("policy"), dict)
            or set(data["policy"]) != {"release_accuracy_requires", "rule"}
            or not isinstance(data["policy"]["release_accuracy_requires"], list)
            or len(data["policy"]["release_accuracy_requires"]) < 5
            or not isinstance(data["policy"]["rule"], str)
            or not isinstance(data.get("datasets"), list)):
        raise ValueError("invalid corpus registry root contract")
    ids = set()
    for index, row in enumerate(data["datasets"], 1):
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError(f"dataset {index} has missing or unexpected fields")
        if (not isinstance(row["id"], str) or not ID.fullmatch(row["id"])
                or row["id"] in ids or row["tier"] not in TIERS
                or row["status"] not in STATUSES
                or any(not isinstance(row[field], str) or not row[field].strip()
                       for field in FIELDS)):
            raise ValueError(f"dataset {index} has invalid values")
        ids.add(row["id"])
        if row["tier"] in {"candidate_research", "restricted_research",
                           "discovery_only"} and row["status"] == "measured":
            raise ValueError(f"{row['id']} is measured despite its non-release tier")
        mismatch_text = (row["result"] + row["label_semantics"]).lower()
        if (row["status"] == "not_run_for_slop_accuracy"
                and not any(term in mismatch_text for term in ("slop", "provenance",
                                                                "authorship"))):
            raise ValueError(f"{row['id']} does not explain its label mismatch")
    required = {"aistoryhub", "beemo", "slop-index", "raid", "mage", "hc3",
                "arb", "editlens", "maga-bench", "m4gt-bench",
                "coling-2025-mgt", "m4", "autextification", "no-robots",
                "blog-authorship", "enron", "persuade-2", "llm-excess-vocab",
                "slop-forensics", "slopbench", "wikipedia-signs"}
    missing = required - ids
    if missing:
        raise ValueError("registry omits requested sources: " + ", ".join(sorted(missing)))
    return data


def main():
    try:
        data = validate()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"corpus registry: {exc}", file=sys.stderr)
        return 2
    tiers = {}
    for row in data["datasets"]:
        tiers[row["tier"]] = tiers.get(row["tier"], 0) + 1
    print(f"corpus registry: {len(data['datasets'])} sources; "
          + ", ".join(f"{key}={tiers[key]}" for key in sorted(tiers)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
