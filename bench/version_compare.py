#!/usr/bin/env python3
"""Interleave a released scorer and the working scorer on frozen workloads."""
import argparse
import hashlib
import importlib.util
import json
import platform
import statistics as st
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "bench" / "version-comparison.json"


def load_module(root, name):
    path = root / "scripts" / "slopscore.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def version(root):
    return json.loads((root / ".codex-plugin" / "plugin.json").read_text())["version"]


def tracked_documents():
    rows = []
    for path in sorted((ROOT / "data" / "corpus" / "must-not-flag").glob("*.txt")):
        rows.append((f"must-not-flag/{path.name}", path.read_text(), "human"))
    search = json.loads((ROOT / "bench" / "search-corpus" / "corpus.json").read_text())
    rows.extend((f"search/{row['id']}", row["text"], "slop") for row in search)
    quality = json.loads((ROOT / "bench" / "quality-corpus" / "manifest.json").read_text())
    rows.extend((f"quality/{row['id']}", row["text"], "quality")
                for row in quality["items"])
    discrimination = json.loads((ROOT / "bench" / "discrimination" / "corpus.json").read_text())
    rows.extend((f"discrimination/{row['id']}", row["text"], row["label"])
                for row in discrimination)
    return rows


def quality_metrics(module, data, docs):
    manifest = json.loads((ROOT / "bench" / "quality-corpus" / "manifest.json").read_text())
    labels = []
    for name in ("labels-rater-a.json", "labels-rater-b.json"):
        payload = json.loads((ROOT / "bench" / "quality-corpus" / name).read_text())
        labels.append({row["id"]: row["label"] for row in payload["items"]})
    by_id = {name.split("/", 1)[1]: text for name, text, _ in docs
             if name.startswith("quality/")}
    tp = tn = fp = fn = 0
    for row in manifest["items"]:
        votes = {label[row["id"]] for label in labels}
        if len(votes) != 1 or next(iter(votes)) not in {"clean", "sloppy"}:
            continue
        truth = next(iter(votes))
        predicted = module.score_text(by_id[row["id"]], data)["ai_likelihood"] >= 25
        tp += truth == "sloppy" and predicted
        tn += truth == "clean" and not predicted
        fp += truth == "clean" and predicted
        fn += truth == "sloppy" and not predicted
    return {"items": tp + tn + fp + fn, "true_positive": tp, "true_negative": tn,
            "false_positive": fp, "false_negative": fn,
            "accuracy": round((tp + tn) / (tp + tn + fp + fn), 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", required=True, type=Path)
    parser.add_argument("--candidate-root", type=Path, default=ROOT)
    parser.add_argument("--runs", type=int, default=12,
                        help="interleaved timing runs per version (default: 12)")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    baseline_root, candidate_root = args.baseline_root.resolve(), args.candidate_root.resolve()
    baseline = load_module(baseline_root, "slopscore_baseline")
    candidate = load_module(candidate_root, "slopscore_candidate")
    baseline_data, candidate_data = baseline.load_patterns(), candidate.load_patterns()
    docs = tracked_documents()

    timing_docs = [
        (ROOT / "data" / "corpus" / "must-not-flag" / "technical-postmortem.txt").read_text(),
        next(text for name, text, _ in docs if name == "search/linkedin-lessons-01"),
        (ROOT / "data" / "corpus" / "must-not-flag" / "personal-essay.txt").read_text(),
    ]
    repeats, copies = args.runs, 200
    if repeats < 6:
        parser.error("--runs must be at least 6")

    def exercise(module, data):
        for _ in range(copies):
            for text in timing_docs:
                module.score_text(text, data)

    exercise(baseline, baseline_data)
    exercise(candidate, candidate_data)
    times = {"baseline": [], "candidate": []}
    for index in range(repeats):
        order = (("baseline", baseline, baseline_data),
                 ("candidate", candidate, candidate_data))
        if index % 2:
            order = tuple(reversed(order))
        for label, module, data in order:
            started = time.perf_counter()
            exercise(module, data)
            times[label].append(time.perf_counter() - started)

    projections = {}
    for label, module, data in (("baseline", baseline, baseline_data),
                                ("candidate", candidate, candidate_data)):
        projections[label] = {
            name: module.score_text(text, data)["ai_likelihood"]
            for name, text, _ in docs
        }
    changed = [name for name in projections["baseline"]
               if projections["baseline"][name] != projections["candidate"][name]]
    safety = [name for name, _, label in docs if label == "human"]
    search = [name for name, _, _ in docs if name.startswith("search/")]

    adversarial = {
        "zero_width_known_phrase": "We should del\u200bve into the intricate tapestry before launch.",
        "mixed_script_known_phrase": "We should d\u0435lv\u0435 into the intricate tapestry before launch.",
        "chat_roleplay_action": "I understand. *nods thoughtfully* Here is the answer.",
        "expanded_tool_tracker": "Read https://example.com/?utm_source=claude.ai for details.",
        "long_low_word_variety": "The system runs the task and checks the task. " * 30,
        "reasoning_artifact": "Let me think step by step before I answer.",
        "novelty_inflation": "This is the failure mode nobody is naming.",
        "emotional_flatline": "What surprised me most was the final result.",
        "acknowledgment_loop": "To answer your question, the cache expires hourly.",
    }
    adversarial_scores = {
        key: {
            "baseline": baseline.score_text(text, baseline_data)["ai_likelihood"],
            "candidate": candidate.score_text(text, candidate_data)["ai_likelihood"],
        }
        for key, text in adversarial.items()
    }
    structured = {
        "fenced_code": ("```py\nprint('safe')\n```", "```py\nprint('changed')\n```"),
        "frontmatter": ("---\ndraft: false\n---\n\nText.", "---\ndraft: true\n---\n\nText."),
        "inline_and_path": ("Run `check.py` from ./scripts/check.py.",
                            "Run `test.py` from ./scripts/test.py."),
        "capitalized_magnitude": ("Acme raised $4.2M.", "Acme raised $4.9M."),
        "bare_relative_path": ("Run scripts/slopscore.py.",
                               "Run scripts/register.py."),
        "heading_level": ("# Title\n\n## Detail", "# Title\n\n### Detail"),
    }
    structured_results = {
        key: {
            "baseline_blocks": not baseline.fidelity(before, after)["preserved"],
            "candidate_blocks": not candidate.fidelity(before, after)["preserved"],
        }
        for key, (before, after) in structured.items()
    }

    recorded_times = {
        label: [round(value, 4) for value in values]
        for label, values in times.items()
    }
    baseline_median = st.median(recorded_times["baseline"])
    candidate_median = st.median(recorded_times["candidate"])
    result = {
        "result_kind": "interleaved_local_version_comparison",
        "measured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "environment": {"platform": platform.system(), "architecture": platform.machine(),
                        "python": platform.python_version()},
        "baseline": {"version": version(baseline_root),
                     "commit": subprocess_commit(baseline_root),
                     "slopscore_sha256": digest((baseline_root / "scripts" / "slopscore.py").read_text())},
        "candidate": {"version": version(candidate_root),
                      "slopscore_sha256": digest((candidate_root / "scripts" / "slopscore.py").read_text())},
        "workload": {"documents_per_run": len(timing_docs) * copies,
                     "runs_per_version": repeats, "warm_cache": True,
                     "alternating_order": True,
                     "tracked_documents": len(docs)},
        "timing_seconds": {
            "baseline": recorded_times["baseline"],
            "candidate": recorded_times["candidate"],
            "median_baseline": round(baseline_median, 4),
            "median_candidate": round(candidate_median, 4),
            "documents_per_second_baseline": round(len(timing_docs) * copies / baseline_median, 1),
            "documents_per_second_candidate": round(len(timing_docs) * copies / candidate_median, 1),
            "median_speed_change_pct": round((baseline_median / candidate_median - 1) * 100, 2),
        },
        "frozen_regression": {
            "score_changes": len(changed), "changed_document_ids": changed,
            "known_human_below_gate_baseline": sum(projections["baseline"][name] < 25 for name in safety),
            "known_human_below_gate_candidate": sum(projections["candidate"][name] < 25 for name in safety),
            "known_human_documents": len(safety),
            "search_slop_caught_baseline": sum(projections["baseline"][name] >= 25 for name in search),
            "search_slop_caught_candidate": sum(projections["candidate"][name] >= 25 for name in search),
            "search_documents": len(search),
            "quality_baseline": quality_metrics(baseline, baseline_data, docs),
            "quality_candidate": quality_metrics(candidate, candidate_data, docs),
        },
        "new_adversarial_detection": adversarial_scores,
        "new_structured_fidelity": structured_results,
        "limits": "Local scorer comparison on one machine. It excludes AI editing time and is not a service-level guarantee. The frozen quality labels are consensus calls from two LLM editorial raters, not human field accuracy.",
    }
    rendered = json.dumps(result, indent=1) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
        print(f"wrote {OUTPUT}")
    else:
        print(rendered, end="")
    return 0


def subprocess_commit(root):
    import subprocess
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                          capture_output=True, text=True, check=True).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
