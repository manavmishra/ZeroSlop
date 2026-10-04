#!/usr/bin/env python3
"""Fresh offline deterministic replay; no timing, model calls, or new labels.

The output is a new measurement of exact working bytes, not an equivalence
admission or a relabelling of historical LLM-rated research.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

from pinned_runtime import ROOT, populate, scorer
from runtime_compatibility import PINNED_FILES, exact_code_compatible
from validate_corpus_registry import validate
from version_compare import tracked_documents, quality_metrics

OUT = ROOT / "bench/release-replay-2.12.16.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compute():
    registry = validate()
    admitted = {row["id"]: row for row in registry["datasets"]}
    for name in ("zero-slop-search-corpus", "zero-slop-quality-panel"):
        if admitted[name]["status"] != "measured":
            raise ValueError("replay corpus has not been admitted")
    version = json.loads((ROOT / "package.json").read_text())["version"]
    if version != "2.12.16":
        raise ValueError("this receipt is specifically a 2.12.16 replay")
    spec = importlib.util.spec_from_file_location("surface_replay", ROOT / "bench/feature-ablation/check.py")
    surface = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(surface)
    with tempfile.TemporaryDirectory() as temp:
        current = scorer(ROOT, "current_release_replay")
        current.HOME = Path(temp) / "empty-private-home"
        baseline_root = populate(Path(temp) / "baseline", "2.12.13")
        baseline = scorer(baseline_root, "baseline_release_replay")
        baseline_hashes = {name: sha(baseline_root / name) for name in sorted(PINNED_FILES)}
        current_data, baseline_data = current.load_patterns(), baseline.load_patterns()
        docs = tracked_documents()
        projections = {
            label: {name: module.score_text(text, patterns)["ai_likelihood"]
                    for name, text, _ in docs}
            for label, module, patterns in (("historical", baseline, baseline_data),
                                            ("current", current, current_data))
        }
        changed = [name for name, value in projections["historical"].items()
                   if projections["current"][name] != value]
        human = [name for name, _, label in docs if label == "human"]
        search = [name for name, _, _ in docs if name.startswith("search/")]
        count, vector = surface.surface_hash(current)
        old_count, old_vector = surface.surface_hash(baseline)
        panel = quality_metrics(current, current_data, docs)
        old_panel = quality_metrics(baseline, baseline_data, docs)
    source_paths = {name for name in PINNED_FILES}
    source_paths.update({"package.json", "bench/corpus-registry.json",
                         "bench/release_replay.py", "bench/version_compare.py",
                         "bench/feature-ablation/check.py", "bench/pinned_runtime.py",
                         "bench/examples.json", "bench/search-corpus/corpus.json",
                         "bench/discrimination/corpus.json", "bench/quality-corpus/manifest.json",
                         "bench/quality-corpus/labels-rater-a.json",
                         "bench/quality-corpus/labels-rater-b.json"})
    source_paths.update(str(path.relative_to(ROOT))
                        for path in (ROOT / "data/corpus/must-not-flag").glob("*.txt"))
    if any(exact_code_compatible("2.12.12", release) for release in ("2.12.13", "2.12.14", "2.12.15")):
        raise ValueError("modified current bytes unexpectedly admitted as historical code")
    return {
        "schema": 1, "result_kind": "fresh_deterministic_release_replay",
        "version": version, "private_preferences": "excluded",
        "raw_sha256": {name: sha(ROOT / name) for name in sorted(source_paths)},
        "historical_comparison": {"version": "2.12.13",
            "commit": "5dc573740f79b32449ec5f25e9a1c443e7ab8e36",
            "raw_sha256": baseline_hashes},
        "surface": {"documents": count, "score_vector_sha256": vector,
                    "historical_documents": old_count, "historical_score_vector_sha256": old_vector},
        "regression": {"documents": len(docs), "changed_document_ids": changed,
                       "known_human_documents": len(human),
                       "known_human_below_gate": sum(projections["current"][name] < 25 for name in human),
                       "search_documents": len(search),
                       "search_caught": sum(projections["current"][name] >= 25 for name in search)},
        "frozen_llm_labels": {"current_surface": panel, "historical_surface": old_panel,
                              "new_judging": False, "field_accuracy": False},
        "limits": "Deterministic scorer replay on frozen bundled inputs only. Output parity is not code equivalence, new labels, a timing measurement, full workflow validation, or human field accuracy. Historical records remain unchanged.",
    }


def check(receipt):
    expected = dict(receipt)
    datetime.fromisoformat(expected.pop("measured_at"))
    if expected != compute():
        raise ValueError("fresh release replay drifted; independent review is required")
    regression = receipt["regression"]
    if (regression["changed_document_ids"]
            or regression["known_human_below_gate"] != regression["known_human_documents"]
            or regression["search_caught"] != regression["search_documents"]
            or receipt["frozen_llm_labels"]["current_surface"] != receipt["frozen_llm_labels"]["historical_surface"]):
        raise ValueError("deterministic release regression")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        if OUT.exists():
            raise ValueError("refusing to overwrite a measured receipt")
        result = compute()
        result["measured_at"] = datetime.now(timezone.utc).isoformat()
        OUT.write_text(json.dumps(result, indent=2) + "\n")
    else:
        result = json.loads(OUT.read_text())
        check(result)
    print(f"2.12.16 deterministic replay: {result['surface']['documents']} surface / {result['regression']['documents']} regression documents; no new judging")


if __name__ == "__main__":
    main()
