"""Fresh replay provenance and regression checks without mutating any source."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import release_replay


class FreshReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(release_replay.receipt_path().read_text())
        cls.current = release_replay.compute()

    def test_actual_receipt_matches_exact_current_bytes_and_outputs(self):
        release_replay.check(self.receipt)
        self.assertEqual(self.receipt["version"], release_replay.current_version())
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
        wrong_version = "2.12.18" if self.receipt["version"] != "2.12.18" else "2.12.19"
        for key, value in (("version", wrong_version), ("private_preferences", "included")):
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

    def test_historical_16_receipt_is_immutable_and_not_current_evidence(self):
        path = release_replay.ROOT / "bench/release-replay-2.12.16.json"
        self.assertEqual(release_replay.sha(path),
                         "b262dc696f975ecb4522846f40de1532442a2aa5f2d467ff980052abe31e4f32")
        historical = json.loads(path.read_text())
        self.assertEqual(historical["version"], "2.12.16")
        if self.receipt["version"] != "2.12.16":
            with mock.patch.object(release_replay, "compute", return_value=self.current):
                with self.assertRaisesRegex(ValueError, "drifted"):
                    release_replay.check(historical)
                relabelled = copy.deepcopy(historical)
                relabelled["version"] = self.receipt["version"]
                with self.assertRaisesRegex(ValueError, "drifted"):
                    release_replay.check(relabelled)


class VersionAndWriteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "bench").mkdir()
        patch = mock.patch.object(release_replay, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def package(self, version):
        (self.root / "package.json").write_text(json.dumps({"version": version}))

    def test_current_17_selects_a_new_path_without_touching_16(self):
        self.package("2.12.17")
        historical = self.root / "bench/release-replay-2.12.16.json"
        historical.write_text("immutable historical bytes")
        result = {"version": "2.12.17", "surface": {"documents": 152},
                  "regression": {"documents": 114}}
        with mock.patch.object(release_replay, "compute", return_value=result), \
                mock.patch("sys.argv", ["release_replay.py", "--write"]), \
                mock.patch("builtins.print"):
            release_replay.main()
            with self.assertRaisesRegex(ValueError, "overwrite"):
                release_replay.main()
        self.assertEqual(release_replay.current_version(), "2.12.17")
        self.assertEqual(release_replay.receipt_path().name, "release-replay-2.12.17.json")
        self.assertEqual(json.loads(release_replay.receipt_path().read_text())["version"], "2.12.17")
        self.assertEqual(historical.read_text(), "immutable historical bytes")

    def test_unsupported_versions_and_path_injection_fail_before_measurement(self):
        for version in (None, 17, True, "", "2.12", "v2.12.17", "02.12.17",
                        "2.012.17", "2.12.017", "2.12.17-rc.1", "2.12.17+build",
                        "2.12.17\n", " 2.12.17", "../../2.12.17", "2.12.17/../../x",
                        "2.12.17\\x", "２.12.17"):
            with self.subTest(version=version):
                self.package(version)
                with mock.patch.object(release_replay, "validate") as validate:
                    for action in (release_replay.receipt_path, release_replay.compute):
                        with self.assertRaisesRegex(ValueError, "unsupported"):
                            action()
                    validate.assert_not_called()

    def test_version_change_during_write_fails_without_a_receipt(self):
        self.package("2.12.17")
        def changed():
            self.package("2.12.18")
            return {"version": "2.12.17"}
        with mock.patch.object(release_replay, "compute", side_effect=changed), \
                mock.patch("sys.argv", ["release_replay.py", "--write"]):
            with self.assertRaisesRegex(ValueError, "changed during replay"):
                release_replay.main()
        self.assertEqual(list((self.root / "bench").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
