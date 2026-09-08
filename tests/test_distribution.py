#!/usr/bin/env python3
"""Cover the packaging surfaces: the PyPI mirror, the Action reporter, the hook.

    python3 -m unittest tests.test_distribution

Stdlib only, no network. These guard the three artefacts that carry Zero Slop
outside the agent ecosystem, so a broken one is caught before a release rather
than by a user's CI.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT / "scripts"))

import build_pypi  # noqa: E402
import gha_report  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PyPIMirror(unittest.TestCase):
    def test_mirror_is_current(self):
        self.assertEqual(build_pypi.main(["--check"]), 0,
                         "packaging/zero_slop is stale; run python3 tooling/build_pypi.py")

    def test_scorer_bytes_are_identical(self):
        for name in build_pypi.MODULES:
            with self.subTest(module=name):
                self.assertEqual(
                    digest(ROOT / "scripts" / name),
                    digest(build_pypi.PACKAGE / "scripts" / name),
                    f"{name} in the wheel differs from the shipped scorer",
                )

    def test_data_bytes_are_identical(self):
        for name in build_pypi.DATA:
            with self.subTest(data=name):
                self.assertEqual(
                    digest(ROOT / "data" / name),
                    digest(build_pypi.PACKAGE / "data" / name),
                )

    def test_data_resolves_from_the_package_layout(self):
        """slopscore reads ../data relative to itself; the mirror must preserve that."""
        spec = importlib.util.spec_from_file_location(
            "_mirrored_slopscore", build_pypi.PACKAGE / "scripts" / "slopscore.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        patterns = module.load_patterns()
        self.assertGreater(len(patterns["patterns"]), 0)

    def test_wheel_version_matches_package_json(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        version = json.loads((ROOT / "package.json").read_text())["version"]
        self.assertIn(f'version = "{version}"', pyproject,
                      "pyproject.toml version must match package.json")


class ActionReporter(unittest.TestCase):
    def _run(self, report: dict, gate: float = 25.0, path: str = ""):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            report_file = tmp / "r.json"
            report_file.write_text(json.dumps(report), encoding="utf-8")
            out, summary = tmp / "out.txt", tmp / "sum.md"
            out.touch(); summary.touch()
            env = {"GITHUB_OUTPUT": str(out), "GITHUB_STEP_SUMMARY": str(summary),
                   "GITHUB_WORKSPACE": str(tmp)}
            previous = {k: os.environ.get(k) for k in env}
            os.environ.update(env)
            try:
                argv = ["--gate", str(gate), "--report", str(report_file)]
                if path:
                    argv += ["--path", path]
                code = gha_report.main(argv)
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            return code, out.read_text(), summary.read_text()

    def test_batch_report_fails_above_the_gate(self):
        code, out, summary = self._run({
            "items": [{"file": "/w/a.md", "score": 99.9, "band": "major rewrite"},
                      {"file": "/w/b.md", "score": 9.5, "band": "clear"}]})
        self.assertEqual(code, 0)
        self.assertIn("passed=false", out)
        self.assertIn("max-score=99.9", out)
        self.assertIn("documents=2", out)
        self.assertIn("| File | Score | Band |", summary)

    def test_batch_report_passes_below_the_gate(self):
        _, out, _ = self._run({"items": [{"file": "/w/b.md", "score": 9.5, "band": "clear"}]})
        self.assertIn("passed=true", out)

    def test_single_file_report_uses_the_scored_path(self):
        """A flat report has no filename; without --path the annotation points nowhere."""
        rows = gha_report.normalise({"ai_likelihood": 99.9}, "docs/bad.md")
        self.assertEqual(rows[0]["file"], "docs/bad.md")
        self.assertEqual(rows[0]["score"], 99.9)

    def test_relative_never_escapes_the_workspace(self):
        self.assertEqual(gha_report.relative("docs/a.md", "/w"), "docs/a.md")
        self.assertEqual(gha_report.relative("/w/docs/a.md", "/w"), "docs/a.md")
        # Outside the workspace: keep the absolute path rather than emit ../..
        self.assertEqual(gha_report.relative("/elsewhere/a.md", "/w"), "/elsewhere/a.md")

    def test_unreadable_report_is_an_error_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "nope.json"
            self.assertEqual(gha_report.main(["--gate", "25", "--report", str(bad)]), 1)

    def test_annotations_only_cover_documents_above_the_gate(self):
        rows = [{"file": "/w/a.md", "score": 99.9, "band": "x"},
                {"file": "/w/b.md", "score": 1.0, "band": "clear"}]
        lines = gha_report.annotations(rows, 25.0, "/w")
        self.assertEqual(len(lines), 1)
        self.assertIn("file=a.md", lines[0])
        self.assertIn("not who wrote it", lines[0])


class ActionManifest(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "action.yml").read_text(encoding="utf-8")

    def test_marketplace_requirements_present(self):
        for field in ("name:", "description:", "branding:", "icon:", "color:"):
            self.assertIn(field, self.text, f"action.yml needs {field} for the Marketplace")

    def test_inputs_reach_the_shell_through_env(self):
        """Interpolating inputs straight into run: is a script-injection vector."""
        run_block = self.text.split("run: |", 1)[1]
        self.assertNotIn("${{ inputs.", run_block,
                         "action.yml must pass inputs via env:, not expression interpolation")

    def test_description_fits_the_marketplace_limit(self):
        """GitHub refuses to publish an Action whose description reaches 125 characters."""
        line = next(l for l in self.text.splitlines() if l.startswith("description:"))
        description = line.split(":", 1)[1].strip().strip('"')
        self.assertLess(len(description), 125,
                        f"description is {len(description)} characters")
        self.assertGreater(len(description), 0)

    def test_calls_the_shipped_scorer_and_reporter(self):
        self.assertIn("scripts/slopscore.py", self.text)
        self.assertIn("tooling/gha_report.py", self.text)


class PreCommitHooks(unittest.TestCase):
    def test_hook_ids_and_entry(self):
        text = (ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
        self.assertIn("- id: zero-slop", text)
        self.assertIn("entry: zero-slop-gate", text)
        self.assertIn("language: python", text)

    def test_console_script_is_declared(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('zero-slop-gate = "zero_slop.scripts.gate:main"', pyproject,
                      "the pre-commit entry needs a matching console script")
        self.assertIn('slopscore = "zero_slop.scripts.slopscore:main"', pyproject)


class MultiFileGate(unittest.TestCase):
    """pre-commit hands over every matched file at once; the gate must accept a list."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "tooling"))
        import gate
        self.gate = gate
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "bad.md").write_text(
            "We are thrilled to announce a transformative, cutting-edge solution.", encoding="utf-8")
        (self.dir / "good.md").write_text("The cache expires after 15 minutes.", encoding="utf-8")
        (self.dir / "empty.md").write_text("   \n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_many_files_at_once_fails_on_the_worst(self):
        code = self.gate.main(["--gate", "25",
                               str(self.dir / "bad.md"), str(self.dir / "good.md")])
        self.assertEqual(code, 1)

    def test_all_clean_passes(self):
        self.assertEqual(self.gate.main(["--gate", "25", str(self.dir / "good.md")]), 0)

    def test_no_files_is_a_no_op(self):
        self.assertEqual(self.gate.main(["--gate", "25"]), 0)

    def test_empty_file_is_skipped_not_scored(self):
        self.assertEqual(self.gate.main(["--gate", "25", str(self.dir / "empty.md")]), 0)

    def test_unreadable_file_reports_rather_than_crashes(self):
        self.assertEqual(self.gate.main(["--gate", "25", str(self.dir / "nope.md")]), 1)

    def test_gate_boundary_is_inclusive(self):
        """A score exactly at the gate passes; only above it fails."""
        import slopscore
        data = slopscore.load_patterns()
        score = float(slopscore.score_text(
            (self.dir / "good.md").read_text(), data)["ai_likelihood"])
        self.assertEqual(self.gate.main(["--gate", str(score), str(self.dir / "good.md")]), 0)


if __name__ == "__main__":
    unittest.main()
