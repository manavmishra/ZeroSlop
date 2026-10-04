#!/usr/bin/env python3
"""Recompute the surface vector and validate the production/research boundary."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RESULTS = HERE / "results.json"
sys.path.insert(0, str(ROOT / "scripts"))
import slopscore  # noqa: E402
sys.path.insert(0, str(ROOT / "bench"))
from pinned_runtime import populate, scorer  # noqa: E402


def surface_hash(module=slopscore):
    data = module.load_patterns()
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
            score = module.score_text(
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
                     "structured_contextual_research", "reason_labelled_retrieval",
                     "blind_evaluation_lane", "production_verdict"}
    if not isinstance(data, dict) or set(data) != expected_root or data.get("schema") != 1:
        raise ValueError("invalid feature-ablation root contract")
    # This remains a historical 2.12.13 measurement, not a current-release claim.
    with tempfile.TemporaryDirectory() as temp:
        historical_root = populate(Path(temp), "2.12.13")
        historical = scorer(historical_root, "historical_ablation_scorer")
        count, digest = surface_hash(historical)
        candidate = data["candidate"]
        for name, field in (("scripts/slopscore.py", "slopscore_sha256"),
                            ("data/patterns.json", "patterns_sha256"),
                            ("data/learned.json", "learned_sha256")):
            if hashlib.sha256((historical_root / name).read_bytes()).hexdigest() != candidate[field]:
                raise ValueError("historical candidate raw source hash mismatch")
    surface = data["deterministic_surface_ablation"]
    quality = json.loads((ROOT / "bench" / "quality-corpus" / "results.json").read_text())
    current_accuracy = quality["surface_meter"]["accuracy"]
    baseline_accuracy = surface.get("blind_quality_consensus_accuracy_baseline")
    if (surface.get("documents") != count
            or surface.get("candidate_score_vector_sha256") != digest
            or surface.get("exactly_unchanged") is not False
            or surface.get("blind_quality_consensus_accuracy_candidate")
            != current_accuracy
            or not isinstance(baseline_accuracy, (int, float))
            or current_accuracy <= baseline_accuracy
            or surface.get("accuracy_change_percentage_points")
            != round((current_accuracy - baseline_accuracy) * 100, 2)):
        raise ValueError("production-path surface ablation is stale")
    observed = quality["contextual_research_ablation"]["held_out_test_mean"]
    research = data["structured_contextual_research"]
    if (research.get("held_out_test_accuracy") != observed["contextual_accuracy"]
            or research.get("surface_accuracy_on_same_items")
            != observed["surface_accuracy_on_same_items"]
            or research.get("accuracy_change_percentage_points")
            != round(observed["contextual_minus_surface_accuracy"] * 100, 2)
            or research.get("field_accuracy") is not False):
        raise ValueError("contextual research ablation is stale")
    if data.get("candidate", {}).get("production_path") != "single":
        raise ValueError("candidate must declare one production path")
    measured_version = data.get("candidate", {}).get("version")
    if measured_version != "2.12.13":
        raise ValueError("historical candidate version mismatch")
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
    surface = data["deterministic_surface_ablation"]
    print(f"historical 2.12.13 feature ablation: {surface['documents']} production-path documents; "
          f"consensus-panel accuracy +{surface['accuracy_change_percentage_points']:.2f} pp; "
          f"contextual research +{data['structured_contextual_research']['accuracy_change_percentage_points']:.2f} pp "
          "(LLM-rated panels, not field accuracy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
