#!/usr/bin/env python3
"""Offline analysis of frozen editorial experiments; no inference or label creation.

Inputs: --corpus (existing drafts/expected_label/target_spans schema), --runs
and --judgments (each {"methods": {name: [{"id": ..., ...}]}}). Run rows use
text, optional flagged, findings, and/or pipelineResult. Portable findings may
use span instead of quote. Actions edit/ask are actionable; keep is not. An
exact-source actionable finding can establish detection even when output is
missing, but never establishes an available edit or successful removal.
Judgment rows use
source_preservation and voice: preserved/lost/uncertain/missing; target_removal:
removed/partial/not_removed/uncertain/missing. Optional violations contain kind,
source_quote, output_quote (empty for an omission). Source losses require these
exact-source/output anchors. gap_asked is an optional judgment, never a removal.

Blind judges must not receive gold labels/targets. An analyst maps their semantic
evidence to gold targets after judging. A removed outcome requires
annotation_source="post_judging" and target_removal_evidence entries covering
every exact target text with source_quote, a nonblank semantic rationale, and
target_not_paraphrased=true. This records an analyst judgment, not a conclusion
computed from lexical deletion. Missing evidence becomes missing removal.

Absent output or judgment stays unknown. Output differences establish an edit,
not its quality. Exact quote localization uses Python Unicode code-point offsets;
repeated quotes are ambiguous and get no span credit without explicit offsets.
All 60 intended drafts remain in primary denominators. Smaller panels are
descriptive and cannot pass the 60-case preregistered screen.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random

SEED = 20261122
RESAMPLES = 10000
STATES = {"preserved", "lost", "uncertain", "missing"}
REMOVAL = {"removed", "partial", "not_removed", "uncertain", "missing"}
METRICS = ("recall", "precision", "specificity", "clean_no_edit_rate",
           "successful_removal_rate", "source_claim_loss_rate", "context_loss_rate")


def indexed(rows, allowed, description):
    result = {}
    if not isinstance(rows, list):
        raise ValueError(f"{description}: expected rows")
    for row in rows:
        if not isinstance(row, dict) or row.get("id") not in allowed or row["id"] in result:
            raise ValueError(f"{description}: unknown or duplicate id")
        result[row["id"]] = row
    return result


def validate_corpus(corpus):
    rows = corpus.get("drafts")
    if not isinstance(rows, list) or not rows:
        raise ValueError("corpus: expected nonempty drafts")
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or row["id"] in seen or not isinstance(row.get("text"), str)
                or not isinstance(row.get("source_group"), str)
                or row.get("expected_label") not in {"clean", "slop"}
                or not isinstance(row.get("target_spans"), list)):
            raise ValueError("corpus: invalid or duplicate draft")
        seen.add(row["id"])
        if (row["expected_label"] == "slop") != bool(row["target_spans"]):
            raise ValueError("corpus: slop requires targets and clean requires none")
        for target in row["target_spans"]:
            start, end = target.get("start"), target.get("end")
            if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(row["text"])
                    or target.get("text") != row["text"][start:end]):
                raise ValueError("corpus: target offsets/text mismatch")
    return rows


def finding_span(finding, text):
    if not isinstance(finding, dict):
        return None
    start, end = finding.get("start"), finding.get("end")
    quote = finding.get("quote")
    if type(start) is int and type(end) is int and 0 <= start < end <= len(text):
        return (start, end) if quote is None or quote == text[start:end] else None
    if isinstance(quote, str) and quote and text.count(quote) == 1:
        start = text.index(quote)
        return start, start + len(quote)
    return None


def observations(drafts, run_rows, judge_rows):
    allowed = {row["id"] for row in drafts}
    runs = indexed(run_rows, allowed, "runs")
    judges = indexed(judge_rows, allowed, "judgments")
    observations = []
    for draft in drafts:
        run = runs.get(draft["id"], {})
        pipeline = run.get("pipelineResult", {})
        if not isinstance(pipeline, dict):
            raise ValueError("pipelineResult must be an object")
        text = run.get("text", pipeline.get("text"))
        if text is not None and not isinstance(text, str):
            raise ValueError("run text must be a string or null")
        review = pipeline.get("contextualReview", run.get("review", {}))
        if not isinstance(review, dict):
            raise ValueError("review must be an object")
        findings = run.get("findings", review.get("findings", []))
        if not isinstance(findings, list):
            raise ValueError("findings must be a list")
        findings = [{**item, "quote": item.get("quote", item.get("span"))}
                    if isinstance(item, dict) else item for item in findings]
        grounded = [item for item in findings if isinstance(item, dict) and (
            finding_span(item, draft["text"]) or isinstance(item.get("quote"), str)
            and item["quote"] and item["quote"] in draft["text"])]
        questions = [item for item in grounded if item.get("action") != "keep"
                     and isinstance(item.get("question"), str)
                     and item["question"].strip()
                     and item.get("kind") in {"missing_substance", "unsupported_claim"}]
        if "flagged" in run and run["flagged"] is not None and type(run["flagged"]) is not bool:
            raise ValueError("flagged must be boolean or null")
        actionable = [item for item in grounded if isinstance(item.get("reason"), str) and item["reason"].strip()
                      and (item.get("action") in {"edit", "ask"} or "action" not in item
                           and item.get("kind") in {"style", "redundancy", "missing_substance", "unsupported_claim"})]
        if "flagged" in run:
            flagged = run["flagged"]
        elif text is not None and text != draft["text"]:
            flagged = True
        elif review.get("decision") == "gap":
            flagged = True if questions else None
        elif actionable:
            flagged = True
        elif (review.get("decision") == "keep" and not actionable) or pipeline.get("status") == "already_clear":
            flagged = False
        elif text == draft["text"] and grounded and all(item.get("action") == "keep" for item in grounded):
            flagged = False
        else:
            flagged = None
        before = pipeline.get("before")
        surface_flag = None
        if isinstance(before, dict):
            surface_flag = bool(before.get("flags") or before.get("flaggedPhrases")
                                or before.get("register", {}).get("findings") or before.get("shape", {}).get("broetry"))
        judge = judges.get(draft["id"], {})
        for key in ("source_preservation", "voice"):
            if judge.get(key, "missing") not in STATES:
                raise ValueError(f"invalid judgment {key}")
        if judge.get("target_removal", "missing") not in REMOVAL:
            raise ValueError("invalid target_removal")
        if "gap_asked" in judge and type(judge["gap_asked"]) is not bool:
            raise ValueError("gap_asked must be boolean")
        violations = judge.get("violations", [])
        if not isinstance(violations, list):
            raise ValueError("violations must be a list")
        for violation in violations:
            if (not isinstance(violation, dict) or not isinstance(violation.get("kind"), str)
                    or not isinstance(violation.get("source_quote"), str)
                    or not violation["source_quote"] or violation["source_quote"] not in draft["text"]
                    or not isinstance(violation.get("output_quote"), str)
                    or text is None or violation["output_quote"] not in text):
                raise ValueError("ungrounded context-loss violation")
        if text is not None and judge.get("source_preservation") == "lost" and not violations:
            raise ValueError("source loss requires grounded violations")
        source = judge.get("source_preservation", "missing") if text is not None else "missing"
        voice = judge.get("voice", "missing") if text is not None else "missing"
        removal = judge.get("target_removal", "missing") if text is not None else "missing"
        positive = draft["expected_label"] == "slop"
        removal_evidence = judge.get("target_removal_evidence", [])
        if not isinstance(removal_evidence, list):
            raise ValueError("target_removal_evidence must be a list")
        for item in removal_evidence:
            if (not isinstance(item, dict) or not isinstance(item.get("source_quote"), str)
                    or not item["source_quote"] or item["source_quote"] not in draft["text"]
                    or not isinstance(item.get("rationale"), str) or not item["rationale"].strip()
                    or ("output_quote" in item and (not isinstance(item["output_quote"], str)
                        or text is None or item["output_quote"] not in text))):
                raise ValueError("ungrounded target-removal evidence")
        removal_evidence_missing = positive and removal == "removed" and not (
            judge.get("annotation_source") == "post_judging" and all(
                any(item["source_quote"] == target["text"] and item.get("target_not_paraphrased") is True
                    for item in removal_evidence) for target in draft["target_spans"]))
        if removal_evidence_missing:
            removal = "missing"
        spans = [finding_span(item, draft["text"]) for item in actionable]
        hits = sum(any(span and max(0, min(span[1], target["end"]) - max(span[0], target["start"])) * 2
                       >= target["end"] - target["start"] for span in spans)
                   for target in draft["target_spans"])
        safe = source == voice == "preserved"
        observations.append({
            "id": draft["id"], "group": draft["source_group"], "genre": draft.get("genre", "unknown"),
            "positive": positive, "flagged": flagged, "output_available": text is not None,
            "detection_abstention": flagged is None and text is not None,
            "edited": None if text is None else text != draft["text"],
            "source": source, "voice": voice, "removal": removal,
            "removal_evidence_missing": removal_evidence_missing,
            "target_removal_evidence": removal_evidence,
            "successful_removal": positive and removal == "removed" and safe,
            "source_claim_loss": source == "lost",
            "context_loss": source == "lost" or voice == "lost",
            "gap_asked": bool(questions) and judge.get("gap_asked") is True,
            "source_only_gap": bool(questions) and judge.get("gap_asked") is True and safe,
            "detection_channel": run.get("detection_channel", "operational_edit_or_contextual_finding"),
            "native_surface_flag": surface_flag,
            "target_count": len(draft["target_spans"]), "span_hits": hits,
            "lexical_target_absent": None if text is None else sum(target["text"] not in text for target in draft["target_spans"]),
            "violations": violations,
        })
    return observations


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def summarize(rows):
    positives = sum(row["positive"] for row in rows)
    clean = len(rows) - positives
    tp = sum(row["positive"] and row["flagged"] is True for row in rows)
    fp = sum(not row["positive"] and row["flagged"] is True for row in rows)
    tn = sum(not row["positive"] and row["flagged"] is False for row in rows)
    no_edit = sum(not row["positive"] and row["edited"] is False for row in rows)
    removals = sum(row["successful_removal"] for row in rows)
    losses = sum(row["source_claim_loss"] for row in rows)
    context = sum(row["context_loss"] for row in rows)
    return {
        "intended": len(rows), "source_groups": len({row["group"] for row in rows}), "positive": positives, "clean": clean,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": positives - tp,
                      "unknown_clean": sum(not row["positive"] and row["flagged"] is None for row in rows)},
        "positive_abstentions_in_fn": sum(row["positive"] and row["detection_abstention"] for row in rows),
        "observed_detection_abstentions": sum(row["detection_abstention"] for row in rows),
        "recall": ratio(tp, positives), "precision": ratio(tp, tp + fp), "specificity": ratio(tn, clean),
        "clean_flag_rate": ratio(fp, clean),
        "clean_actual_edit_rate": ratio(sum(not row["positive"] and row["edited"] is True for row in rows), clean),
        "clean_no_edit_count": no_edit, "clean_no_edit_rate": ratio(no_edit, clean),
        "span_recall": ratio(sum(row["span_hits"] for row in rows), sum(row["target_count"] for row in rows)),
        "target_count": sum(row["target_count"] for row in rows),
        "native_surface_flag_count": sum(row["native_surface_flag"] is True for row in rows),
        "native_surface_unmeasured_count": sum(row["native_surface_flag"] is None for row in rows),
        "successful_removal_count": removals, "successful_removal_rate": ratio(removals, positives),
        "partial_removal_count": sum(row["positive"] and row["removal"] == "partial" for row in rows),
        "lexical_target_absent_count": sum(row["lexical_target_absent"] or 0 for row in rows),
        "gap_asked_count": sum(row["gap_asked"] for row in rows),
        "source_only_gap_count": sum(row["source_only_gap"] for row in rows),
        "source_claim_loss_count": losses, "source_claim_loss_rate": ratio(losses, len(rows)),
        "context_loss_count": context, "context_loss_rate": ratio(context, len(rows)),
        "violated_claims": dict(Counter(item["kind"] for row in rows for item in row["violations"])),
        "missing": {"outputs": sum(not row["output_available"] for row in rows),
                    "detection": sum(row["flagged"] is None and not row["detection_abstention"] for row in rows),
                    "source": sum(row["source"] == "missing" for row in rows),
                    "voice": sum(row["voice"] == "missing" for row in rows),
                    "positive_removal": sum(row["positive"] and row["removal"] == "missing" for row in rows)},
        "removed_claims_without_semantic_evidence": sum(row["removal_evidence_missing"] for row in rows),
        "uncertain": {"source": sum(row["source"] == "uncertain" for row in rows),
                      "voice": sum(row["voice"] == "uncertain" for row in rows),
                      "positive_removal": sum(row["positive"] and row["removal"] == "uncertain" for row in rows)},
    }


def percentile(values, probability):
    values = sorted(values)
    position = (len(values) - 1) * probability
    lo, hi = math.floor(position), math.ceil(position)
    return values[lo] + (values[hi] - values[lo]) * (position - lo)


def paired_bootstrap(candidate, baseline):
    groups = defaultdict(list)
    for left, right in zip(candidate, baseline):
        if left["id"] != right["id"] or left["group"] != right["group"]:
            raise ValueError("paired rows must have identical ids and source groups")
        groups[left["group"]].append((left, right))
    def totals(rows):
        return (len(rows), sum(row["positive"] for row in rows),
                sum(row["positive"] and row["flagged"] is True for row in rows),
                sum(not row["positive"] and row["flagged"] is True for row in rows),
                sum(not row["positive"] and row["flagged"] is False for row in rows),
                sum(not row["positive"] and row["edited"] is False for row in rows),
                sum(row["successful_removal"] for row in rows),
                sum(row["source_claim_loss"] for row in rows),
                sum(row["context_loss"] for row in rows))

    def metrics(counts):
        n, positive, tp, fp, tn, no_edit, removal, loss, context = counts
        return dict(zip(METRICS, (ratio(tp, positive), ratio(tp, tp + fp), ratio(tn, n - positive),
                                 ratio(no_edit, n - positive), ratio(removal, positive), ratio(loss, n), ratio(context, n))))

    keys = sorted(groups)
    grouped = {key: (totals([pair[0] for pair in groups[key]]),
                     totals([pair[1] for pair in groups[key]])) for key in keys}
    rng = random.Random(SEED)
    values = {name: [] for name in METRICS}
    for _ in range(RESAMPLES):
        sample = [grouped[key] for key in rng.choices(keys, k=len(keys))]
        left = metrics(tuple(map(sum, zip(*(pair[0] for pair in sample)))))
        right = metrics(tuple(map(sum, zip(*(pair[1] for pair in sample)))))
        for name in METRICS:
            if left[name] is not None and right[name] is not None:
                values[name].append(left[name] - right[name])
    left, right = summarize(candidate), summarize(baseline)
    return {name: {"difference": None if left[name] is None or right[name] is None else left[name] - right[name],
                   "ci95": [percentile(samples, .025), percentile(samples, .975)] if samples else None,
                   "interval_excludes_zero": bool(samples) and (percentile(samples, .025) > 0 or percentile(samples, .975) < 0),
                   "defined_resamples": len(samples), "undefined_resamples": RESAMPLES - len(samples)}
            for name, samples in values.items()}


def discordances(candidate, baseline, outcome):
    pairs = [(a, b) for a, b in zip(candidate, baseline) if a[outcome] is not None and b[outcome] is not None]
    wins = [a for a, b in pairs if a[outcome] and not b[outcome]]
    losses = [a for a, b in pairs if b[outcome] and not a[outcome]]
    n = len(wins) + len(losses)
    p = min(1., 2 * sum(math.comb(n, k) for k in range(min(len(wins), len(losses)) + 1)) / 2 ** n) if n else 1.
    return {"candidate_only_drafts": len(wins), "baseline_only_drafts": len(losses),
            "candidate_only_groups": len({row["group"] for row in wins}),
            "baseline_only_groups": len({row["group"] for row in losses}),
            "unresolved_pairs": len(candidate) - len(pairs), "exact_two_sided_p_exploratory": p}


def gain_screen(candidate, baseline, intervals):
    def complete(summary):
        # An observed unchanged failure is an abstention, not absent coverage.
        # It still misses positive detection/removal; it never certifies safety.
        required = ("outputs", "source", "voice", "positive_removal")
        return not any(summary["missing"][key] for key in required) and not any(summary["uncertain"].values())
    scope = candidate["intended"] == baseline["intended"] == 60 and candidate["clean"] == baseline["clean"] == 30
    gates = {
        "primary_60_case_scope": scope,
        "complete_matched_evidence": complete(candidate) and complete(baseline),
        "recall_plus_10pp": candidate["recall"] is not None and baseline["recall"] is not None and candidate["recall"] - baseline["recall"] >= .10 - 1e-12,
        "precision_no_lower": candidate["precision"] is not None and baseline["precision"] is not None and candidate["precision"] >= baseline["precision"],
        "clean_no_edit_29_of_30": scope and candidate["clean_no_edit_count"] >= 29,
        "clean_no_edit_no_more_than_one_worse": candidate["clean_no_edit_count"] >= baseline["clean_no_edit_count"] - 1,
        "zero_observed_source_claim_losses": candidate["source_claim_loss_count"] == 0,
        "successful_removal_no_lower": candidate["successful_removal_rate"] is not None and baseline["successful_removal_rate"] is not None and candidate["successful_removal_rate"] >= baseline["successful_removal_rate"],
    }
    ci = intervals["recall"]["ci95"]
    return {"gates": gates, "failed": [name for name, passed in gates.items() if not passed],
            "point_screen_passed": all(gates.values()),
            "recall_gain_statistically_supported": all(gates.values()) and ci is not None and ci[0] > 0,
            "publication_authorized": False}


def evaluate(corpus, runs, judgments, baseline):
    drafts = validate_corpus(corpus)
    methods = runs.get("methods")
    judge_methods = judgments.get("methods")
    if not isinstance(methods, dict) or not isinstance(judge_methods, dict) or baseline not in methods:
        raise ValueError("expected methods maps containing the named baseline")
    if set(judge_methods) - set(methods):
        raise ValueError("judgments contain an unknown method")
    rows = {name: observations(drafts, records, judge_methods.get(name, [])) for name, records in methods.items()}
    summaries = {name: summarize(records) for name, records in rows.items()}
    comparisons = {}
    for name, records in rows.items():
        if name == baseline:
            continue
        intervals = paired_bootstrap(records, rows[baseline])
        comparisons[name] = {"candidate_minus_baseline": intervals,
                             "screen": gain_screen(summaries[name], summaries[baseline], intervals),
                             "user_acceptance_condition": {
                                 "zero_observed_context_or_voice_losses": summaries[name]["context_loss_count"] == 0,
                                 "resolved_source_and_voice_judging": not any(
                                     summaries[name][state][key] for state in ("missing", "uncertain") for key in ("source", "voice")),
                                 "all_outputs_available": summaries[name]["missing"]["outputs"] == 0,
                             },
                             "discordances_exploratory": {key: discordances(records, rows[baseline], key)
                               for key in ("flagged", "edited", "successful_removal", "source_claim_loss", "context_loss")}}
    return {"schema": "zs-editorial-evaluation-1", "baseline": baseline,
            "detection_rule": "Changed returned text or an actionable exact-source contextual finding is positive; a concrete gap question detects but does not remove. already_clear/valid keep without actionable findings is negative. Unchanged failures without actionable findings abstain. Explicit flagged is reserved for separately declared native operating points.",
            "bootstrap": {"resamples": RESAMPLES, "seed": SEED, "unit": "paired source group", "interval": "percentile 95%"},
            "summaries": summaries, "comparisons": comparisons,
            "per_genre": {name: {genre: summarize([row for row in records if row["genre"] == genre])
                                     for genre in sorted({row["genre"] for row in records})}
                          for name, records in rows.items()},
            "observations": rows,
            "limitations": ["Synthetic author labels and model judgments are not human truth.",
                            "Missing and uncertain judgments are not evidence of safety or success.",
                            "Loss rates use intended denominators; unknown counts must accompany them.",
                            "Gap questions and lexical absence are separate from successful semantic removal.",
                            "Exploratory draft-level p-values do not remove within-source correlation.",
                            "No result from this tool authorizes publication or proves production quality."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("corpus", "runs", "judgments"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--baseline", required=True)
    args = parser.parse_args()
    artifacts = {name: getattr(args, name).read_bytes() for name in ("corpus", "runs", "judgments")}
    report = evaluate(*(json.loads(artifacts[name]) for name in ("corpus", "runs", "judgments")), args.baseline)
    report["input_sha256"] = {name: hashlib.sha256(raw).hexdigest() for name, raw in artifacts.items()}
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
