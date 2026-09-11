"""Fail-closed regression tests for the narrowly pinned measurement exception."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from runtime_compatibility import (
    EVIDENCE, PINNED_FILES, ROOT, exact_code_compatible, reports_match,
)


class RuntimeCompatibilityTests(unittest.TestCase):
    def test_exact_reviewed_pair_matches(self):
        self.assertTrue(exact_code_compatible("2.11.6", "2.12.0"))

    def test_unknown_or_reversed_versions_rejected(self):
        for pair in [("2.11.5", "2.12.0"), ("2.11.6", "2.12.1"),
                     ("2.12.0", "2.11.6"), ("2.11.6", "2.11.6"),
                     (None, "2.12.0")]:
            with self.subTest(pair=pair):
                self.assertFalse(exact_code_compatible(*pair))

    def test_every_source_and_data_change_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in PINNED_FILES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            self.assertTrue(exact_code_compatible("2.11.6", "2.12.0", root=root))
            for name in PINNED_FILES:
                with self.subTest(file=name):
                    target = root / name
                    original = target.read_bytes()
                    target.write_bytes(original + b"\n")
                    self.assertFalse(exact_code_compatible("2.11.6", "2.12.0", root=root))
                    target.write_bytes(original)

    def test_missing_files_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(exact_code_compatible("2.11.6", "2.12.0", root=Path(temp)))

    def test_incomplete_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.json"
            record = json.loads(EVIDENCE.read_text())
            del record["files"]["data/learned.json"]
            path.write_text(json.dumps(record))
            self.assertFalse(exact_code_compatible("2.11.6", "2.12.0", evidence_path=path))

    def test_invalid_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.json"
            path.write_text("invalid json")
            self.assertFalse(exact_code_compatible("2.11.6", "2.12.0", evidence_path=path))

    def test_only_verified_version_difference_accepted_without_mutation(self):
        old = {"scorer": {"version": "2.11.6"}, "score": 12, "date": "historical"}
        new = {"scorer": {"version": "2.12.0"}, "score": 12, "date": "historical"}
        before = copy.deepcopy((old, new))
        self.assertTrue(reports_match(old, new))
        self.assertEqual((old, new), before)
        new["score"] = 13
        self.assertFalse(reports_match(old, new))
        new["score"] = 12
        new["date"] = "relabelled"
        self.assertFalse(reports_match(old, new))

    def test_version_only_difference_cannot_bypass_modified_runtime(self):
        old = {"scorer": {"version": "2.11.6"}, "score": 12}
        new = {"scorer": {"version": "2.12.0"}, "score": 12}
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(reports_match(old, new, root=Path(temp)))


if __name__ == "__main__":
    unittest.main()
