"""Small fictional fixtures; these tests never read the confirmation corpus."""
import copy
import importlib.util
from pathlib import Path
import random
import unittest


PATH = Path(__file__).resolve().parents[1] / "bench/blind-20261122/evaluate.py"
SPEC = importlib.util.spec_from_file_location("blinded_evaluation", PATH)
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


def fixture(groups=2):
    drafts = []
    runs = []
    judges = []
    for group in range(groups):
        for positive in (False, True):
            identifier = f"{group}-{'slop' if positive else 'clean'}"
            text = "The pilot may run Friday." + (" Seamless progress." if positive else "")
            start = text.find("Seamless")
            drafts.append({"id": identifier, "source_group": str(group), "genre": "technical",
                           "text": text, "expected_label": "slop" if positive else "clean",
                           "target_spans": [{"start": start, "end": len(text), "text": text[start:]}] if positive else []})
            runs.append({"id": identifier, "text": "The pilot may run Friday.",
                         "review": {"decision": "edit" if positive else "keep", "findings": [
                             {"quote": "Seamless progress.", "kind": "style", "reason": "No distinct information."}
                         ] if positive else []}})
            judges.append({"id": identifier, "source_preservation": "preserved", "voice": "preserved",
                           "target_removal": "removed" if positive else "not_removed",
                           "annotation_source": "post_judging", "target_removal_evidence": [{
                               "source_quote": "Seamless progress.", "rationale": "The unsupported benefit is absent and is not restated.",
                               "target_not_paraphrased": True}] if positive else []})
    return {"drafts": drafts}, runs, judges


class EvaluationTests(unittest.TestCase):
    def test_confusion_separates_clean_flag_from_actual_edit(self):
        corpus, runs, judges = fixture()
        runs[0]["review"] = {"decision": "edit", "findings": [
            {"quote": "pilot", "kind": "style", "reason": "A claimed concern."}]}
        rows = evaluation.observations(corpus["drafts"], runs, judges)
        summary = evaluation.summarize(rows)
        self.assertEqual(summary["confusion"], {"tp": 2, "fp": 1, "tn": 1, "fn": 0, "unknown_clean": 0})
        self.assertEqual(summary["clean_flag_rate"], .5)
        self.assertEqual(summary["clean_actual_edit_rate"], 0)
        self.assertEqual(summary["successful_removal_rate"], 1)

    def test_missing_judgments_and_outputs_never_become_safe_success(self):
        corpus, runs, _ = fixture(1)
        rows = evaluation.observations(corpus["drafts"], runs[:1], [])
        summary = evaluation.summarize(rows)
        self.assertEqual(summary["missing"], {"outputs": 1, "detection": 1, "source": 2, "voice": 2, "positive_removal": 1})
        self.assertEqual(summary["successful_removal_count"], 0)
        self.assertEqual(summary["confusion"]["fn"], 1)
        self.assertIsNone(summary["precision"])

    def test_operational_edit_detection_and_unchanged_failure_abstention(self):
        corpus, _, judges = fixture(1)
        runs = [{"id": corpus["drafts"][0]["id"], "pipelineResult": {
            "status": "rewritten_with_warnings", "text": "Friday's pilot may run.",
            "before": {"flags": [], "flaggedPhrases": 0}}},
            {"id": corpus["drafts"][1]["id"], "pipelineResult": {
                "status": "unchanged_verification_failed", "text": corpus["drafts"][1]["text"]}}]
        rows = evaluation.observations(corpus["drafts"], runs, judges)
        self.assertIs(rows[0]["flagged"], True)
        self.assertIs(rows[0]["native_surface_flag"], False)
        self.assertIsNone(rows[1]["flagged"])

    def test_gap_question_detects_without_receiving_removal_credit(self):
        corpus, runs, judges = fixture(1)
        positive = corpus["drafts"][1]
        runs[1]["text"] = positive["text"]
        runs[1]["review"] = {"decision": "gap", "findings": [{
            "quote": "Seamless progress.", "kind": "missing_substance", "reason": "No outcome is supplied.",
            "question": "What outcome is supported?"}]}
        judges[1].update(target_removal="not_removed", gap_asked=True)
        summary = evaluation.summarize(evaluation.observations(corpus["drafts"], runs, judges))
        self.assertEqual(summary["recall"], 1)
        self.assertEqual(summary["source_only_gap_count"], 1)
        self.assertEqual(summary["successful_removal_count"], 0)
        self.assertEqual(summary["lexical_target_absent_count"], 0)

    def test_portable_keep_findings_do_not_flag_clean_text_but_actual_edit_does(self):
        corpus, runs, judges = fixture(1)
        runs[0].pop("review")
        runs[0]["findings"] = [{"span": "may run", "action": "keep",
                                "kind": "style", "reason": "The uncertainty is necessary."}]
        rows = evaluation.observations(corpus["drafts"], runs, judges)
        self.assertIs(rows[0]["flagged"], False)
        runs[0]["text"] = "The pilot may run on Friday."
        self.assertIs(evaluation.observations(corpus["drafts"], runs, judges)[0]["flagged"], True)

    def test_portable_ask_reason_detects_without_inventing_question_or_output(self):
        corpus, runs, judges = fixture(1)
        runs[1] = {"id": runs[1]["id"], "findings": [{"span": "Seamless progress.", "action": "ask",
                   "reason": "Ask the writer which actual outcome this describes."}]}
        result = evaluation.observations(corpus["drafts"], runs, judges)[1]
        self.assertIs(result["flagged"], True)
        self.assertFalse(result["gap_asked"])
        self.assertFalse(result["output_available"])
        self.assertFalse(result["successful_removal"])

    def test_retaining_a_positive_target_does_not_count_as_span_detection(self):
        corpus, runs, judges = fixture(1)
        runs[1] = {"id": corpus["drafts"][1]["id"], "text": corpus["drafts"][1]["text"],
                   "findings": [{"span": "Seamless progress.", "action": "keep",
                                 "reason": "The method considers this justified."}]}
        row = evaluation.observations(corpus["drafts"], runs, judges)[1]
        self.assertIs(row["flagged"], False)
        self.assertEqual(row["span_hits"], 0)

    def test_span_half_overlap_uses_codepoints_and_repeated_quotes_abstain(self):
        text = "😀abc😀abc"
        self.assertIsNone(evaluation.finding_span({"quote": "😀abc"}, text))
        self.assertEqual(evaluation.finding_span({"quote": "😀abc", "start": 4, "end": 8}, text), (4, 8))
        corpus, runs, judges = fixture(1)
        target = corpus["drafts"][1]["target_spans"][0]
        half = (target["end"] - target["start"] + 1) // 2
        runs[1]["findings"] = [{"start": target["start"], "end": target["start"] + half}]
        self.assertEqual(evaluation.observations(corpus["drafts"], runs, judges)[1]["span_hits"], 1)
        runs[1]["findings"][0]["end"] -= 1
        self.assertEqual(evaluation.observations(corpus["drafts"], runs, judges)[1]["span_hits"], 0)

    def test_lexical_absence_does_not_override_uncertain_or_partial_judgment(self):
        corpus, runs, judges = fixture(1)
        judges[1]["target_removal"] = "partial"
        judges[1]["source_preservation"] = "uncertain"
        summary = evaluation.summarize(evaluation.observations(corpus["drafts"], runs, judges))
        self.assertEqual(summary["lexical_target_absent_count"], 1)
        self.assertEqual(summary["successful_removal_count"], 0)
        self.assertEqual(summary["partial_removal_count"], 1)
        self.assertEqual(summary["uncertain"]["source"], 1)

    def test_removed_without_post_judging_semantic_evidence_is_unknown(self):
        corpus, runs, judges = fixture(1)
        judges[1].pop("target_removal_evidence")
        summary = evaluation.summarize(evaluation.observations(corpus["drafts"], runs, judges))
        self.assertEqual(summary["successful_removal_count"], 0)
        self.assertEqual(summary["missing"]["positive_removal"], 1)
        self.assertEqual(summary["removed_claims_without_semantic_evidence"], 1)
        self.assertEqual(summary["lexical_target_absent_count"], 1)

    def test_loss_requires_source_output_evidence_and_is_counted_by_claim(self):
        corpus, runs, judges = fixture(1)
        runs[1]["text"] = "The pilot will run Friday."
        judges[1]["source_preservation"] = "lost"
        with self.assertRaisesRegex(ValueError, "requires grounded"):
            evaluation.observations(corpus["drafts"], runs, judges)
        judges[1]["violations"] = [{"kind": "modality", "source_quote": "may run", "output_quote": "will run"}]
        summary = evaluation.summarize(evaluation.observations(corpus["drafts"], runs, judges))
        self.assertEqual(summary["violated_claims"], {"modality": 1})
        self.assertEqual(summary["source_claim_loss_count"], 1)
        self.assertEqual(summary["successful_removal_count"], 0)
        judges[1]["violations"][0]["output_quote"] = "never appears"
        with self.assertRaisesRegex(ValueError, "ungrounded"):
            evaluation.observations(corpus["drafts"], runs, judges)

    def test_bootstrap_preserves_pairs_and_counts_undefined_precision(self):
        corpus, runs, judges = fixture(2)
        baseline = copy.deepcopy(runs)
        for row in baseline:
            row["flagged"] = False
        left = evaluation.observations(corpus["drafts"], runs, judges)
        right = evaluation.observations(corpus["drafts"], baseline, judges)
        result = evaluation.paired_bootstrap(left, right)
        self.assertEqual(result["recall"]["ci95"], [1, 1])
        self.assertEqual(result["precision"]["undefined_resamples"], 10000)
        self.assertIsNone(result["precision"]["ci95"])
        self.assertEqual(evaluation.paired_bootstrap(left, right), result)
        right.reverse()
        with self.assertRaisesRegex(ValueError, "paired rows"):
            evaluation.paired_bootstrap(left, right)

    def test_primary_screen_needs_60_complete_cases_and_nonzero_interval(self):
        corpus, runs, judges = fixture(30)
        left = evaluation.summarize(evaluation.observations(corpus["drafts"], runs, judges))
        right = copy.deepcopy(left)
        right["recall"] = .9
        intervals = {"recall": {"ci95": [0, .2]}}
        screen = evaluation.gain_screen(left, right, intervals)
        self.assertTrue(screen["point_screen_passed"])
        self.assertFalse(screen["recall_gain_statistically_supported"])
        self.assertFalse(screen["publication_authorized"])
        left["missing"]["source"] = 1
        self.assertIn("complete_matched_evidence", evaluation.gain_screen(left, right, intervals)["failed"])
        left["missing"]["source"] = 0
        left["clean_no_edit_count"] = 28
        self.assertIn("clean_no_edit_29_of_30", evaluation.gain_screen(left, right, intervals)["failed"])

    def test_observed_abstention_is_a_miss_but_not_missing_coverage(self):
        corpus, runs, judges = fixture(30)
        runs[1] = {"id": runs[1]["id"], "pipelineResult": {
            "status": "unchanged_no_better_version", "text": corpus["drafts"][1]["text"]}}
        judges[1]["target_removal"] = "not_removed"
        rows = evaluation.observations(corpus["drafts"], runs, judges)
        summary = evaluation.summarize(rows)
        self.assertEqual(summary["observed_detection_abstentions"], 1)
        self.assertEqual(summary["missing"]["detection"], 0)
        self.assertEqual(summary["confusion"]["fn"], 1)
        intervals = {"recall": {"ci95": [0, .2]}}
        screen = evaluation.gain_screen(summary, summary, intervals)
        self.assertTrue(screen["gates"]["complete_matched_evidence"])
        self.assertFalse(screen["gates"]["recall_plus_10pp"])
        runs.pop(1)
        missing = evaluation.summarize(evaluation.observations(corpus["drafts"], runs, judges))
        self.assertFalse(evaluation.gain_screen(missing, summary, intervals)["gates"]["complete_matched_evidence"])

    def test_voice_loss_fails_separate_user_condition(self):
        corpus, runs, judges = fixture(1)
        judges[0]["voice"] = "lost"
        report = evaluation.evaluate(corpus, {"methods": {"base": runs, "candidate": runs}},
                                     {"methods": {"base": judges, "candidate": judges}}, "base")
        condition = report["comparisons"]["candidate"]["user_acceptance_condition"]
        self.assertFalse(condition["zero_observed_context_or_voice_losses"])
        self.assertTrue(condition["resolved_source_and_voice_judging"])

    def test_precision_undefined_resamples_follow_source_group_draws(self):
        corpus, runs, judges = fixture(2)
        baseline = copy.deepcopy(runs)
        baseline[3]["flagged"] = False
        candidate = evaluation.observations(corpus["drafts"], runs, judges)
        reference = evaluation.observations(corpus["drafts"], baseline, judges)
        rng = random.Random(20261122)
        undefined = sum("0" not in rng.choices(["0", "1"], k=2) for _ in range(10000))
        intervals = evaluation.paired_bootstrap(candidate, reference)
        self.assertEqual(intervals["precision"]["undefined_resamples"], undefined)
        self.assertEqual(intervals["recall"]["ci95"], [0, 1])
        self.assertFalse(intervals["recall"]["interval_excludes_zero"])

    def test_exact_discordance_p_value_and_unresolved_pairs(self):
        candidate = [{"flagged": True, "group": str(index)} for index in range(3)]
        baseline = [{"flagged": False, "group": str(index)} for index in range(3)]
        candidate.append({"flagged": None, "group": "unknown"})
        baseline.append({"flagged": True, "group": "unknown"})
        result = evaluation.discordances(candidate, baseline, "flagged")
        self.assertEqual(result["exact_two_sided_p_exploratory"], .25)
        self.assertEqual(result["candidate_only_groups"], 3)
        self.assertEqual(result["unresolved_pairs"], 1)

    def test_duplicate_ids_and_mismatched_target_offsets_fail_closed(self):
        corpus, runs, judges = fixture(1)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluation.observations(corpus["drafts"], runs + runs[:1], judges)
        corpus["drafts"][1]["target_spans"][0]["start"] += 1
        with self.assertRaisesRegex(ValueError, "offsets/text mismatch"):
            evaluation.validate_corpus(corpus)


if __name__ == "__main__":
    unittest.main()
