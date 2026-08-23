#!/usr/bin/env python3
"""Recompute the current surface vector and validate the v2.4.3→v2.5.0 ablation."""
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RESULTS = HERE / "results.json"
sys.path.insert(0, str(ROOT / "scripts"))
import contextual  # noqa: E402
import slopscore  # noqa: E402


def surface_hash():
    data = slopscore.load_patterns()
    rows = []
    sources = [
        (ROOT / "bench" / "examples.json", "draft", False),
        (ROOT / "bench" / "search-corpus" / "corpus.json", "text", False),
        (ROOT / "bench" / "discrimination" / "corpus.json", "text", False),
        (ROOT / "bench" / "quality-corpus" / "manifest.json", "text", True),
    ]
    for path, field, wrapped in sources:
        payload = json.loads(path.read_text())
        items = payload["items"] if wrapped else payload
        for item in items:
            score = slopscore.score_text(
                item[field], data,
                formal=item.get("genre") in {"research", "professional"},
            )["ai_likelihood"]
            rows.append([item["id"], score])
    blob = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode()
    return len(rows), hashlib.sha256(blob).hexdigest()


def validate():
    data = json.loads(RESULTS.read_text())
    expected_root = {"schema", "baseline", "candidate",
                     "deterministic_surface_ablation",
                     "structured_contextual_shadow", "reason_labelled_retrieval",
                     "blind_evaluation_lane", "interleaved_local_performance",
                     "production_verdict"}
    if not isinstance(data, dict) or set(data) != expected_root or data.get("schema") != 1:
        raise ValueError("invalid feature-ablation root contract")
    count, digest = surface_hash()
    surface = data["deterministic_surface_ablation"]
    if (surface.get("documents") != count
            or surface.get("candidate_score_vector_sha256") != digest
            or surface.get("baseline_score_vector_sha256") != digest
            or surface.get("exactly_unchanged") is not True
            or surface.get("accuracy_change_percentage_points") != 0.0):
        raise ValueError("classic-path surface ablation is stale")
    quality = json.loads((ROOT / "bench" / "quality-corpus" / "results.json").read_text())
    observed = quality["contextual_shadow_ablation"]["held_out_test_mean"]
    shadow = data["structured_contextual_shadow"]
    if (shadow.get("held_out_test_accuracy") != observed["contextual_accuracy"]
            or shadow.get("surface_accuracy_on_same_items")
            != observed["surface_accuracy_on_same_items"]
            or shadow.get("accuracy_change_percentage_points")
            != round(observed["contextual_minus_surface_accuracy"] * 100, 2)
            or shadow.get("field_accuracy") is not False):
        raise ValueError("contextual shadow ablation is stale")
    saved = os.environ.pop("ZERO_SLOP_MODE", None)
    try:
        if contextual.current_mode() != "classic":
            raise ValueError("feature mode no longer defaults to classic")
    finally:
        if saved is not None:
            os.environ["ZERO_SLOP_MODE"] = saved
    retrieval = data["reason_labelled_retrieval"]
    if (retrieval.get("maximum_preferences") != 50000
            or retrieval.get("calibrated_probability") is not False
            or retrieval.get("accuracy_result") is not None):
        raise ValueError("retrieval evidence contract is stale")
    return data


def main():
    try:
        data = validate()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"feature ablation: {exc}", file=sys.stderr)
        return 2
    print("feature ablation: classic surface unchanged on 152 documents; "
          f"contextual shadow +{data['structured_contextual_shadow']['accuracy_change_percentage_points']:.2f} pp "
          "on the blind LLM panel (not field accuracy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
