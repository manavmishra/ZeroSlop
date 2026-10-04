"""Fresh replay provenance and regression checks without mutating any source."""
import copy
import json
import unittest
from unittest import mock

import release_replay


class FreshReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(release_replay.OUT.read_text())
        cls.current = release_replay.compute()

    def test_actual_receipt_matches_exact_current_bytes_and_outputs(self):
        release_replay.check(self.receipt)
        self.assertEqual(self.receipt["version"], "2.12.16")
        self.assertFalse(self.receipt["frozen_llm_labels"]["new_judging"])
        self.assertFalse(self.receipt["frozen_llm_labels"]["field_accuracy"])
        self.assertEqual(self.receipt["surface"]["documents"], 152)
        self.assertEqual(self.receipt["regression"]["documents"], 114)
        self.assertEqual(self.receipt["surface"]["score_vector_sha256"],
                         self.receipt["surface"]["historical_score_vector_sha256"])
        self.assertNotEqual(self.receipt["raw_sha256"]["scripts/slopscore.py"],
                            self.receipt["historical_comparison"]["raw_sha256"]["scripts/slopscore.py"])

    def test_any_recorded_input_hash_change_fails_closed(self):
        for path in self.receipt["raw_sha256"]:
            with self.subTest(path=path):
                altered = copy.deepcopy(self.receipt)
                altered["raw_sha256"][path] = "0" * 64
                with mock.patch.object(release_replay, "compute", return_value=self.current):
                    with self.assertRaisesRegex(ValueError, "drifted"):
                        release_replay.check(altered)

    def test_output_drift_and_version_relabelling_fail_closed(self):
        for key, value in (("version", "2.12.17"), ("private_preferences", "included")):
            altered = copy.deepcopy(self.receipt)
            altered[key] = value
            with mock.patch.object(release_replay, "compute", return_value=self.current):
                with self.assertRaisesRegex(ValueError, "drifted"):
                    release_replay.check(altered)
        altered = copy.deepcopy(self.receipt)
        altered["surface"]["score_vector_sha256"] = "0" * 64
        with mock.patch.object(release_replay, "compute", return_value=self.current):
            with self.assertRaisesRegex(ValueError, "drifted"):
                release_replay.check(altered)

    def test_regressions_cannot_be_approved_by_recording_the_bad_output(self):
        for key, value in (("changed_document_ids", ["changed"]),
                           ("known_human_below_gate", 17), ("search_caught", 17)):
            altered = copy.deepcopy(self.receipt)
            altered["regression"][key] = value
            recomputed = dict(altered)
            recomputed.pop("measured_at")
            with mock.patch.object(release_replay, "compute", return_value=recomputed):
                with self.assertRaisesRegex(ValueError, "regression"):
                    release_replay.check(altered)


if __name__ == "__main__":
    unittest.main()
