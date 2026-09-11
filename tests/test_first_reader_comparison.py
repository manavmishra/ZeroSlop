"""Regression boundaries for a non-rewriting skill in editorial comparisons."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "bench"
spec = importlib.util.spec_from_file_location("comparison_charts", BENCH / "make_charts.py")
charts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(charts)
spec = importlib.util.spec_from_file_location("first_reader_evaluator", BENCH / "first-reader" / "evaluate.py")
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


class FirstReaderComparisonTests(unittest.TestCase):
    def setUp(self):
        self.audit = json.loads((BENCH / "competitor-capabilities.json").read_text())

    def test_all_products_render_and_have_valid_statuses(self):
        data = charts.capability_data(self.audit)
        self.assertEqual(len(data["products"]), len(self.audit["products"]))
        self.assertIn("first_reader", [r[0] for r in data["products"]])
        self.assertTrue(all(len(row) == 1 + len(data["products"]) for row in data["rows"]))

    def test_unknown_status_cannot_silently_render_as_absent(self):
        for status in [None, "unmeasured", 0]:
            audit = copy.deepcopy(self.audit)
            audit["capabilities"][0]["first_reader"] = status
            with self.assertRaises(ValueError):
                charts.capability_data(audit)

    def test_missing_product_cell_is_rejected(self):
        del self.audit["capabilities"][0]["first_reader"]
        with self.assertRaises(ValueError):
            charts.capability_data(self.audit)

    def test_duplicate_capabilities_rejected(self):
        self.audit["capabilities"].append(self.audit["capabilities"][0])
        with self.assertRaises(ValueError):
            charts.capability_data(self.audit)

    def test_new_capabilities_do_not_retroactively_claim_absence(self):
        for row in self.audit["capabilities"]:
            if row["id"] in {"reader_skim_gate", "staged_reader_feed", "transcript_recall", "reader_comment_page", "reader_followup"}:
                self.assertEqual(row["first_reader"], "native")
                for key in self.audit["products"]:
                    if key != "first_reader":
                        self.assertEqual(row[key], "not_assessed")

    def test_component_checks_never_become_reader_accuracy(self):
        results = json.loads((BENCH / "first-reader" / "results.json").read_text())
        self.assertEqual(results["result_kind"], "pinned_source_and_offline_component_contracts")
        self.assertIsNone(results["reader_outcome_accuracy"])
        self.assertIsNone(results["rewrite_scores"])
        self.assertEqual(results["model_calls"], 0)
        self.assertEqual(results["human_readers"], 0)
        self.assertFalse(results["network_during_checks"])
        self.assertEqual(results["passed"], sum(row["passed"] for row in results["checks"]))
        self.assertEqual(results["total"], len(results["checks"]))
        self.assertEqual(results["passed"], results["total"])
        for field, name in [("source_manifest_sha256", "source.json"), ("evaluator_sha256", "evaluate.py")]:
            self.assertEqual(results[field], hashlib.sha256((BENCH / "first-reader" / name).read_bytes()).hexdigest())

    def test_non_rewriter_excluded_from_rewrite_panels(self):
        self.assertFalse(any("first" in label.lower() for label, _ in charts.PANEL))
        manifest = json.loads((BENCH / "chart-data.json").read_text())
        for key in ["detector_panel", "search_rewrite_scores", "search_rewrite_passes", "blind_quality"]:
            self.assertFalse(any("first reader" in label.lower() for label, _ in manifest[key]))

    def test_source_identity_and_license_match_comparison(self):
        source = json.loads((BENCH / "first-reader" / "source.json").read_text())
        product = self.audit["products"]["first_reader"]
        self.assertEqual(product["commit"], source["commit"])
        self.assertEqual(product["license"], source["license"])
        self.assertEqual(source["license"], "Apache-2.0")
        self.assertEqual(len(source["files"]), 14)

    def test_missing_source_rejected_before_external_code_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "missing or changed pinned source"):
                evaluator.evaluate(Path(tmp))

    def test_modified_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text("modified content")
            with self.assertRaisesRegex(ValueError, "missing or changed pinned source"):
                evaluator.verify_source(root, {"files": {"SKILL.md": "0" * 64}})


if __name__ == "__main__":
    unittest.main()
