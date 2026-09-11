#!/usr/bin/env python3
"""Offline contracts for a pinned First Reader source, not reader-outcome accuracy.

--fetch downloads the immutable upstream files into --source-root first. Neither
the imported code nor fixture checks open a socket or call a model. Upstream
Apache-2.0 source is cached locally, never copied into the packaged MIT runtime.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source.json"
RESULTS = HERE / "results.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(root, source):
    for name, expected in source["files"].items():
        path = root / name
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"missing or changed pinned source: {name}")


def fetch(root, source):
    base = f"https://raw.githubusercontent.com/{source['repository']}/{source['commit']}/"
    for name, expected in source["files"].items():
        path = root / name
        if path.exists() and digest(path) == expected:
            continue
        upstream = name if name == "LICENSE" else source["path"] + "/" + name
        with urlopen(base + upstream, timeout=30) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"download hash mismatch: {name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def module(root, name):
    spec = importlib.util.spec_from_file_location("first_reader_audit_" + name,
                                                root / "scripts" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cli(mod, *args):
    output = io.StringIO()
    with patch.object(sys, "argv", [mod.__file__, *map(str, args)]), contextlib.redirect_stdout(output):
        mod.main()
    return output.getvalue()


def evaluate(root):
    source = json.loads(SOURCE.read_text())
    verify_source(root, source)  # Fail before importing any external code.
    checks = []

    def check(name, condition):
        checks.append({"id": name, "passed": bool(condition)})

    # The socket guard also covers loopback. Feed's state machine is exercised
    # directly, without starting its HTTP transport or changing its clock.
    with patch("socket.socket", side_effect=AssertionError("network forbidden in fixture checks")):
        feed = module(root, "feed")
        skim = module(root, "skim")
        signals = module(root, "signals")
        recall = module(root, "recall")
        ask = module(root, "ask")
        skill = (root / "SKILL.md").read_text()
        report = (root / "references" / "report.md").read_text()
        check("rewrite_explicitly_excluded", "never rewrites" in skill and "It never rewrites." in report)
        check("reference_material_has_lookup_route", "lookup tasks" in skill)
        check("short_text_skips_recall", "Skip recall." in skill)
        check("fiction_limits_trust_ledger", "Needle and\n  memory only" in skill)
        check("clean_control_must_not_invent_findings", "Never manufacture findings." in skill)
        check("no_quality_scores_in_report", "No scores, no grades, no percentages of quality." in report)
        check("heading_attached_to_prose", feed.chunk("# Heading\n\n" + "word " * 90)[0].startswith("# Heading\n\n"))
        blob = " ".join("token" + str(i) for i in range(501))
        chunks = feed.chunk(blob)
        check("long_blob_preserves_words", " ".join(chunks).split() == blob.split())
        check("long_blob_has_multiple_passages", len(chunks) > 1 and max(map(lambda c: len(c.split()), chunks)) <= 200)
        check("empty_chunking_is_empty", feed.chunk(" \n\n ") == [])
        with tempfile.TemporaryDirectory(prefix="first-reader-contract-") as tmp:
            tmp = Path(tmp)
            draft = tmp / "draft.md"
            text = "\n\n".join(marker + " " + "ordinary word " * 45
                                 for marker in ["OPENING_SENTINEL", "MIDDLE_SENTINEL", "ENDING_SENTINEL"])
            draft.write_text(text)
            run = tmp / "run"
            state = feed.Feed(draft, run, ["keen", "skeptic"], {"keen": "fixture persona"}, 0.08)
            keen, skeptic = state.readers.values()
            check("cannot_advance_before_start", "error" in state.next(keen, "needle=0 fixture log is long enough"))
            first = state.start(keen)
            check("first_passage_withholds_later_text", "OPENING_SENTINEL" in first["text"] and "MIDDLE_SENTINEL" not in first["text"])
            check("short_log_refused", "refused" in state.next(keen, "short") and keen["cursor"] == 0)
            check("dwell_guard_refuses_racing", "refused" in state.next(keen, "needle=0 fixture log is long enough") and keen["cursor"] == 0)
            check("restart_does_not_advance", state.start(keen)["index"] == 1)
            state.dwell = 0  # No real wait: the positive branch is separate.
            second = state.next(keen, "needle=1 FIXTURE_MEMORY opening raised a question")
            check("valid_log_advances_one_passage", second["index"] == 2 and "MIDDLE_SENTINEL" in second["text"])
            check("draft_state_not_flushed_mid_read", not (run / "keen" / "state.json").exists())
            state.quit(keen, "needle=-2 FIXTURE_MEMORY stopped on the middle")
            check("quit_records_position", keen["quit_at"] == 2 and keen["done"])
            check("one_quit_does_not_flush_other_reader", not (run / "keen" / "state.json").exists())
            state.start(skeptic)
            while not skeptic["done"]:
                state.next(skeptic, "needle=0 FIXTURE_MEMORY recorded this passage")
            check("all_finished_flushes_state", state.closed and (run / "keen" / "state.json").exists())
            check("finished_reader_cannot_advance", "error" in state.next(skeptic, "needle=0 another sufficiently long fixture note"))
            recalled = cli(recall, run / "keen")
            check("recall_receives_memory", "FIXTURE_MEMORY" in recalled and "SAYBACK" in recalled)
            check("recall_withholds_unlogged_draft", all(s not in recalled for s in ["OPENING_SENTINEL", "MIDDLE_SENTINEL", "ENDING_SENTINEL"]))
            answer = ask.bundle(run, "keen", "What remained?")
            check("consultation_uses_log_only", "FIXTURE_MEMORY" in answer and "ENDING_SENTINEL" not in answer)
            check("missing_reader_abstains", ask.bundle(run, "missing", "Question?") is None)
            (run / "skim.txt").write_text("FIXTURE_SKIM stopped at the heading")
            check("skimmer_consultation_uses_own_note", "FIXTURE_SKIM" in ask.bundle(run, "skim", "Why?"))
            draft.write_text("# Fixture heading\n\nFirst visible sentence. HIDDEN_OPENING_TAIL remains hidden here.\n\nSecond visible sentence. HIDDEN_SECOND_TAIL remains hidden here.\n\nOne two three four five six seven eight nine HIDDEN_LATER_TAIL stays outside scanner view.")
            scanned = cli(skim, draft)
            check("scanner_keeps_heading", "# Fixture heading" in scanned)
            check("scanner_truncates_body", all(s not in scanned for s in ["HIDDEN_OPENING_TAIL", "HIDDEN_SECOND_TAIL", "HIDDEN_LATER_TAIL"]))
            draft.write_text("We measured 48 failures in Paris. I was wrong about the rollout. It might recover later.")
            measured = json.loads(cli(signals, draft, "--json"))
            check("signals_count_number", measured["costly"]["numbers"]["count"] == 1)
            check("signals_count_admission", measured["costly"]["admissions_against_interest"]["count"] == 1)
            check("signals_count_hedge", measured["free"]["hedged_sentences"]["count"] == 1)
            check("signals_are_not_quality_score", not any(k in measured for k in ["score", "accuracy", "ai_likelihood"]))
    return {
        "schema": 1,
        "result_kind": "pinned_source_and_offline_component_contracts",
        "source_commit": source["commit"],
        "source_manifest_sha256": digest(SOURCE),
        "evaluator_sha256": digest(Path(__file__)),
        "network_during_checks": False,
        "model_calls": 0,
        "human_readers": 0,
        "reader_outcome_accuracy": None,
        "rewrite_scores": None,
        "checks": checks,
        "passed": sum(r["passed"] for r in checks),
        "total": len(checks),
        "limitations": [
            "Constructed fixtures validate component behavior; no AI reader session or human study was run.",
            "No test suite is present in the pinned first-reader subtree. These are locally authored contracts.",
            "HTTP transport, page rendering, hostile inputs and isolation from agent filesystem access are not validated.",
            "Recall output is a log-bound prompt; this does not measure next-day human memory.",
            "First Reader excludes rewriting and is not ranked in preserved rewrite benchmarks.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.fetch:
        fetch(args.source_root, json.loads(SOURCE.read_text()))
    result = evaluate(args.source_root)
    if args.check:
        if json.loads(RESULTS.read_text()) != result:
            raise SystemExit("First Reader results drifted; regenerate after reviewing changes")
    else:
        RESULTS.write_text(json.dumps(result, indent=2) + "\n")
    print(f"First Reader offline component contracts: {result['passed']}/{result['total']}; reader outcomes unmeasured")
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
