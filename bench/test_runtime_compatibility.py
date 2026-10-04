"""Fail-closed tests for the narrowly pinned measurement exception."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from pinned_runtime import populate

from runtime_compatibility import (
    EVIDENCE, PAIR_EVIDENCE, PINNED_FILES, ROOT,
    exact_code_compatible, reports_match,
)


class RuntimeCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = tempfile.TemporaryDirectory()
        cls.historical = {
            version: populate(Path(cls.archive.name) / version, version)
            for version in ("2.11.6", "2.12.12", "2.12.13")
        }

    @classmethod
    def tearDownClass(cls):
        cls.archive.cleanup()

    def make_evidence(self, path, *, compatible="2.12.0"):
        # Never mint an admission from the code under test.
        record = json.loads(EVIDENCE.read_text())
        record["compatible_version"] = compatible
        path.write_text(json.dumps(record))
        return path

    def copy_runtime(self, destination, measured="2.12.12"):
        for name in PINNED_FILES:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.historical[measured] / name, target)

    def test_historical_evidence_fails_after_runtime_bytes_change(self):
        # These releases matched 2.11.6 when reviewed. The current scorer has
        # since changed, so none may authorize relabelling today.
        for measured, compatible in PAIR_EVIDENCE:
            with self.subTest(pair=(measured, compatible)):
                self.assertFalse(exact_code_compatible(measured, compatible))

    def test_latest_pair_is_exact_and_preserves_historical_results(self):
        self.assertTrue(exact_code_compatible("2.12.12", "2.12.13", root=self.historical["2.12.12"]))
        self.assertFalse(exact_code_compatible("2.12.13", "2.12.12"))
        self.assertFalse(exact_code_compatible("2.12.12", "2.12.16"))
        old = {"scorer": {"version": "2.12.12"}, "score": 12}
        new = {"scorer": {"version": "2.12.13"}, "score": 12}
        before = copy.deepcopy((old, new))
        self.assertTrue(reports_match(old, new, root=self.historical["2.12.12"]))
        self.assertEqual((old, new), before)
        new["score"] = 13
        self.assertFalse(reports_match(old, new))

    def test_latest_pair_rejects_wrong_release_and_changed_bytes(self):
        original = json.loads(PAIR_EVIDENCE[("2.12.12", "2.12.13")].read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"
            self.copy_runtime(root)
            path = Path(temp) / "evidence.json"
            path.write_text(json.dumps(original))
            self.assertTrue(exact_code_compatible("2.12.12", "2.12.13", root=root, evidence_path=path))
            bad = copy.deepcopy(original)
            bad["measured_commit"] = "0d866036b210b90e23fa9f7b4146316cf40c255e"
            path.write_text(json.dumps(bad))
            self.assertFalse(exact_code_compatible("2.12.12", "2.12.13", root=root, evidence_path=path))
            path.write_text(json.dumps(original))
            for name in PINNED_FILES:
                target = root / name
                content = target.read_bytes()
                target.write_bytes(content + b"\n")
                self.assertFalse(exact_code_compatible("2.12.12", "2.12.13", root=root, evidence_path=path))
                target.write_bytes(content)

    def test_complete_exact_hash_evidence_accepts_only_its_reviewed_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = self.make_evidence(Path(temp) / "evidence.json")
            self.assertTrue(exact_code_compatible(
                "2.11.6", "2.12.0", root=self.historical["2.11.6"], evidence_path=evidence,
            ))
            self.assertFalse(exact_code_compatible(
                "2.11.6", "2.12.1", evidence_path=evidence,
            ))
            self.assertFalse(exact_code_compatible(
                "2.12.0", "2.11.6", evidence_path=evidence,
            ))

    def test_reports_match_normalizes_only_the_verified_version(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = self.make_evidence(Path(temp) / "evidence.json")
            old = {"scorer": {"version": "2.11.6"}, "score": 12,
                   "date": "historical"}
            new = {"scorer": {"version": "2.12.0"}, "score": 12,
                   "date": "historical"}
            before = copy.deepcopy((old, new))
            self.assertTrue(reports_match(old, new, root=self.historical["2.11.6"], evidence_path=evidence))
            self.assertEqual((old, new), before)
            new["score"] = 13
            self.assertFalse(reports_match(old, new, root=self.historical["2.11.6"], evidence_path=evidence))
            new["score"] = 12
            new["date"] = "relabelled"
            self.assertFalse(reports_match(old, new, root=self.historical["2.11.6"], evidence_path=evidence))

    def test_identical_reports_need_no_compatibility_exception(self):
        report = {"scorer": {"version": "2.12.10"}, "score": 12}
        self.assertTrue(reports_match(report, copy.deepcopy(report)))

    def test_unknown_current_version_has_no_historical_bypass(self):
        self.assertFalse(exact_code_compatible("2.11.6", "2.12.10"))
        self.assertFalse(exact_code_compatible(None, "2.12.10"))

    def test_every_runtime_source_or_data_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"
            self.copy_runtime(root, "2.11.6")
            evidence = self.make_evidence(Path(temp) / "evidence.json")
            self.assertTrue(exact_code_compatible(
                "2.11.6", "2.12.0", root=root, evidence_path=evidence,
            ))
            for name in PINNED_FILES:
                with self.subTest(file=name):
                    target = root / name
                    original = target.read_bytes()
                    target.write_bytes(original + b"\n")
                    self.assertFalse(exact_code_compatible(
                        "2.11.6", "2.12.0", root=root, evidence_path=evidence,
                    ))
                    target.write_bytes(original)

    def test_missing_runtime_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = self.make_evidence(Path(temp) / "evidence.json")
            self.assertFalse(exact_code_compatible(
                "2.11.6", "2.12.0", root=Path(temp) / "missing",
                evidence_path=evidence,
            ))

    def test_incomplete_or_invalid_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.json"
            record = json.loads(EVIDENCE.read_text())
            del record["files"]["data/learned.json"]
            path.write_text(json.dumps(record))
            self.assertFalse(exact_code_compatible(
                "2.11.6", "2.12.0", root=self.historical["2.11.6"], evidence_path=path,
            ))
            path.write_text("invalid json")
            self.assertFalse(exact_code_compatible(
                "2.11.6", "2.12.0", root=self.historical["2.11.6"], evidence_path=path,
            ))

    def test_2_12_14_admissions_pin_complete_files_and_release_identity(self):
        commits = {
            "2.12.12": "d065464b64d2ae46d72fde83f3c0b5da40bd149a",
            "2.12.13": "5dc573740f79b32449ec5f25e9a1c443e7ab8e36",
        }
        for measured, commit in commits.items():
            with self.subTest(measured=measured):
                evidence = json.loads(PAIR_EVIDENCE[(measured, "2.12.14")].read_text())
                self.assertEqual(evidence["measured_commit"], commit)
                self.assertEqual(set(evidence["files"]), PINNED_FILES)
                self.assertEqual(evidence["measured_version"], measured)
                self.assertEqual(evidence["compatible_version"], "2.12.14")
                self.assertTrue(exact_code_compatible(measured, "2.12.14", root=self.historical[measured]))

    def test_2_12_14_does_not_admit_other_or_reverse_pairs(self):
        for measured, current in (
            ("2.12.11", "2.12.14"), ("2.12.12", "2.12.16"),
            ("2.12.13", "2.12.16"), ("2.12.14", "2.12.12"),
            ("2.12.14", "2.12.13"), (None, "2.12.14"),
        ):
            with self.subTest(pair=(measured, current)):
                self.assertFalse(exact_code_compatible(measured, current))

    def test_2_12_14_rejects_commit_mismatch_and_incomplete_evidence(self):
        for measured in ("2.12.12", "2.12.13"):
            original = json.loads(PAIR_EVIDENCE[(measured, "2.12.14")].read_text())
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "evidence.json"
                for field, value in (
                    ("measured_commit", "0" * 40),
                    ("measured_version", "2.12.11"),
                    ("compatible_version", "2.12.16"),
                    ("schema", 2),
                ):
                    bad = copy.deepcopy(original)
                    bad[field] = value
                    path.write_text(json.dumps(bad))
                    with self.subTest(measured=measured, field=field):
                        self.assertFalse(exact_code_compatible(
                            measured, "2.12.14", evidence_path=path,
                        ))
                for name in PINNED_FILES:
                    bad = copy.deepcopy(original)
                    del bad["files"][name]
                    path.write_text(json.dumps(bad))
                    with self.subTest(measured=measured, missing=name):
                        self.assertFalse(exact_code_compatible(
                            measured, "2.12.14", evidence_path=path,
                        ))
                bad = copy.deepcopy(original)
                bad["files"]["scripts/unreviewed.py"] = "0" * 64
                path.write_text(json.dumps(bad))
                self.assertFalse(exact_code_compatible(
                    measured, "2.12.14", evidence_path=path,
                ))

    def test_2_12_14_rejects_every_pinned_file_hash_drift(self):
        for measured in ("2.12.12", "2.12.13"):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "runtime"
                self.copy_runtime(root, measured)
                self.assertTrue(exact_code_compatible(measured, "2.12.14", root=root))
                for name in PINNED_FILES:
                    target = root / name
                    content = target.read_bytes()
                    target.write_bytes(content + b"\n")
                    with self.subTest(measured=measured, changed=name):
                        self.assertFalse(exact_code_compatible(measured, "2.12.14", root=root))
                    target.write_bytes(content)

    def test_2_12_14_reports_preserve_all_non_version_fields_and_inputs(self):
        for measured in ("2.12.12", "2.12.13"):
            old = {"scorer": {"version": measured, "hash": "same"},
                   "source": {"sha256": "source", "documents": 9},
                   "summary": {"count": 9}, "items": [{"score": 12}],
                   "limits": "historical"}
            new = copy.deepcopy(old)
            new["scorer"]["version"] = "2.12.14"
            before = copy.deepcopy((old, new))
            self.assertTrue(reports_match(old, new, root=self.historical[measured]))
            self.assertEqual((old, new), before)
            for field, value in (
                ("scorer", {"version": "2.12.14", "hash": "changed"}),
                ("source", {"sha256": "changed", "documents": 9}),
                ("summary", {"count": 10}),
                ("items", [{"score": 13}]),
                ("limits", "changed"),
            ):
                bad = copy.deepcopy(new)
                bad[field] = value
                with self.subTest(measured=measured, field=field):
                    self.assertFalse(reports_match(old, bad, root=self.historical[measured]))
                    self.assertEqual((old, new), before)


    def test_2_12_15_admissions_pin_complete_files_and_release_identity(self):
        commits = {
            "2.12.12": "d065464b64d2ae46d72fde83f3c0b5da40bd149a",
            "2.12.13": "5dc573740f79b32449ec5f25e9a1c443e7ab8e36",
        }
        for measured, commit in commits.items():
            with self.subTest(measured=measured):
                evidence = json.loads(PAIR_EVIDENCE[(measured, "2.12.15")].read_text())
                self.assertEqual(evidence["measured_commit"], commit)
                self.assertEqual(set(evidence["files"]), PINNED_FILES)
                self.assertEqual(evidence["measured_version"], measured)
                self.assertEqual(evidence["compatible_version"], "2.12.15")
                self.assertTrue(exact_code_compatible(measured, "2.12.15", root=self.historical[measured]))

    def test_2_12_15_does_not_admit_other_or_reverse_pairs(self):
        for measured, current in (
            ("2.12.11", "2.12.15"), ("2.12.12", "2.12.16"),
            ("2.12.13", "2.12.16"), ("2.12.15", "2.12.12"),
            ("2.12.15", "2.12.13"), (None, "2.12.15"),
        ):
            with self.subTest(pair=(measured, current)):
                self.assertFalse(exact_code_compatible(measured, current))

    def test_2_12_15_rejects_commit_mismatch_and_incomplete_evidence(self):
        for measured in ("2.12.12", "2.12.13"):
            original = json.loads(PAIR_EVIDENCE[(measured, "2.12.15")].read_text())
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "evidence.json"
                for field, value in (
                    ("measured_commit", "0" * 40),
                    ("measured_version", "2.12.11"),
                    ("compatible_version", "2.12.16"),
                    ("schema", 2),
                    ("result_kind", "new_measurement"),
                ):
                    bad = copy.deepcopy(original)
                    bad[field] = value
                    path.write_text(json.dumps(bad))
                    with self.subTest(measured=measured, field=field):
                        self.assertFalse(exact_code_compatible(
                            measured, "2.12.15", evidence_path=path,
                        ))
                for name in PINNED_FILES:
                    bad = copy.deepcopy(original)
                    del bad["files"][name]
                    path.write_text(json.dumps(bad))
                    with self.subTest(measured=measured, missing=name):
                        self.assertFalse(exact_code_compatible(
                            measured, "2.12.15", evidence_path=path,
                        ))
                bad = copy.deepcopy(original)
                bad["files"]["scripts/unreviewed.py"] = "0" * 64
                path.write_text(json.dumps(bad))
                self.assertFalse(exact_code_compatible(
                    measured, "2.12.15", evidence_path=path,
                ))

    def test_2_12_15_rejects_every_pinned_file_hash_drift(self):
        for measured in ("2.12.12", "2.12.13"):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "runtime"
                self.copy_runtime(root, measured)
                self.assertTrue(exact_code_compatible(measured, "2.12.15", root=root))
                for name in PINNED_FILES:
                    target = root / name
                    content = target.read_bytes()
                    target.write_bytes(content + b"\n")
                    with self.subTest(measured=measured, changed=name):
                        self.assertFalse(exact_code_compatible(measured, "2.12.15", root=root))
                    target.write_bytes(content)

    def test_2_12_15_reports_preserve_all_non_version_fields_and_inputs(self):
        for measured in ("2.12.12", "2.12.13"):
            old = {"scorer": {"version": measured, "hash": "same"},
                   "source": {"sha256": "source", "documents": 9},
                   "summary": {"count": 9}, "items": [{"score": 12}],
                   "limits": "historical"}
            new = copy.deepcopy(old)
            new["scorer"]["version"] = "2.12.15"
            before = copy.deepcopy((old, new))
            self.assertTrue(reports_match(old, new, root=self.historical[measured]))
            self.assertEqual((old, new), before)
            for field, value in (
                ("scorer", {"version": "2.12.15", "hash": "changed"}),
                ("source", {"sha256": "changed", "documents": 9}),
                ("summary", {"count": 10}),
                ("items", [{"score": 13}]),
                ("limits", "changed"),
            ):
                bad = copy.deepcopy(new)
                bad[field] = value
                with self.subTest(measured=measured, field=field):
                    self.assertFalse(reports_match(old, bad, root=self.historical[measured]))
                    self.assertEqual((old, new), before)


if __name__ == "__main__":
    unittest.main()
