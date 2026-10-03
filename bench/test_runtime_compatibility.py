"""Fail-closed tests for the narrowly pinned measurement exception."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from runtime_compatibility import (
    EVIDENCE, PAIR_EVIDENCE, PINNED_FILES, ROOT,
    exact_code_compatible, reports_match,
)


class RuntimeCompatibilityTests(unittest.TestCase):
    def make_evidence(self, path, *, compatible="2.12.0", root=ROOT):
        record = {
            "schema": 1,
            "result_kind": "exact_code_equivalence_not_new_measurement",
            "measured_version": "2.11.6",
            "compatible_version": compatible,
            "measured_commit": "0d866036b210b90e23fa9f7b4146316cf40c255e",
            "files": {
                name: hashlib.sha256((Path(root) / name).read_bytes()).hexdigest()
                for name in PINNED_FILES
            },
        }
        path.write_text(json.dumps(record))
        return path

    def copy_runtime(self, destination):
        for name in PINNED_FILES:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_historical_evidence_fails_after_runtime_bytes_change(self):
        # These releases matched 2.11.6 when reviewed. The current scorer has
        # since changed, so none may authorize relabelling today.
        for measured, compatible in PAIR_EVIDENCE:
            if measured != "2.11.6":
                continue
            with self.subTest(pair=(measured, compatible)):
                self.assertFalse(exact_code_compatible(measured, compatible))

    def test_latest_pair_is_exact_and_preserves_historical_results(self):
        self.assertTrue(exact_code_compatible("2.12.12", "2.12.13"))
        self.assertFalse(exact_code_compatible("2.12.13", "2.12.12"))
        self.assertFalse(exact_code_compatible("2.12.12", "2.12.14"))
        old = {"scorer": {"version": "2.12.12"}, "score": 12}
        new = {"scorer": {"version": "2.12.13"}, "score": 12}
        before = copy.deepcopy((old, new))
        self.assertTrue(reports_match(old, new))
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
                "2.11.6", "2.12.0", evidence_path=evidence,
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
            self.assertTrue(reports_match(old, new, evidence_path=evidence))
            self.assertEqual((old, new), before)
            new["score"] = 13
            self.assertFalse(reports_match(old, new, evidence_path=evidence))
            new["score"] = 12
            new["date"] = "relabelled"
            self.assertFalse(reports_match(old, new, evidence_path=evidence))

    def test_identical_reports_need_no_compatibility_exception(self):
        report = {"scorer": {"version": "2.12.10"}, "score": 12}
        self.assertTrue(reports_match(report, copy.deepcopy(report)))

    def test_unknown_current_version_has_no_historical_bypass(self):
        self.assertFalse(exact_code_compatible("2.11.6", "2.12.10"))
        self.assertFalse(exact_code_compatible(None, "2.12.10"))

    def test_every_runtime_source_or_data_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"
            self.copy_runtime(root)
            evidence = self.make_evidence(Path(temp) / "evidence.json", root=root)
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
                "2.11.6", "2.12.0", evidence_path=path,
            ))
            path.write_text("invalid json")
            self.assertFalse(exact_code_compatible(
                "2.11.6", "2.12.0", evidence_path=path,
            ))


if __name__ == "__main__":
    unittest.main()
