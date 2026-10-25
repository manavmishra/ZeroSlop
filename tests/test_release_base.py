"""Resolve release comparisons after normal and rewritten Git history."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HELPER = Path(__file__).resolve().parents[1] / ".github/scripts/release-base.sh"


class ReleaseBase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.remote = self.root / "remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Release test")
        self.git("config", "user.email", "release-test@example.invalid")
        self.base = self.commit("base")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.head = self.commit("current")

    def git(self, *arguments):
        return subprocess.check_output(["git", *arguments], cwd=self.repo, text=True, stderr=subprocess.DEVNULL).strip()

    def commit(self, value):
        (self.repo / "content.txt").write_text(value)
        self.git("add", "content.txt")
        self.git("commit", "-m", value)
        return self.git("rev-parse", "HEAD")

    def resolve(self, **environment):
        return subprocess.run(
            ["bash", str(HELPER)], cwd=self.repo, text=True, capture_output=True,
            env={**os.environ, "EVENT_NAME": "push", "BEFORE": "", "BASE_REF": "", **environment},
        )

    def test_reachable_before_keeps_the_push_delta(self):
        result = self.resolve(BEFORE=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), self.base)
        self.assertEqual(self.git("diff", "--name-only", f"{result.stdout.strip()}...HEAD"), "content.txt")

    def test_missing_before_uses_fetched_main_merge_base(self):
        old_comparison = subprocess.run(
            ["git", "diff", "--name-only", f"{'f' * 40}...HEAD"],
            cwd=self.repo, text=True, capture_output=True,
        )
        self.assertNotEqual(old_comparison.returncode, 0)
        self.assertIn("Invalid symmetric difference", old_comparison.stderr)
        result = self.resolve(BEFORE="f" * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), self.base)
        self.assertIn("merge-base", result.stderr)
        self.assertEqual(self.git("diff", "--name-only", f"{result.stdout.strip()}...HEAD"), "content.txt")

    def test_main_at_head_still_requires_a_bump_for_released_changes(self):
        (self.repo / "package.json").write_text(json.dumps({"version": "2.12.29"}))
        (self.repo / "README.md").write_text("Original documentation.\n")
        self.git("add", "package.json", "README.md")
        previous = self.commit("released version")
        self.git("tag", "v2.12.29")
        (self.repo / "README.md").write_text("Corrected documentation.\n")
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts/runtime.py").write_text("# Released runtime change.\n")
        self.git("add", "README.md", "scripts/runtime.py")
        current = self.commit("released changes without a bump")
        self.git("push", "origin", "main")
        result = self.resolve(BEFORE="f" * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), previous)
        self.assertNotEqual(result.stdout.strip(), current)
        changed = self.git("diff", "--name-only", f"{result.stdout.strip()}...HEAD").splitlines()
        self.assertIn("README.md", changed)
        self.assertIn("scripts/runtime.py", changed)

        sys.path.insert(0, str(HELPER.parents[2] / "scripts"))
        import check_release_version
        with mock.patch.object(check_release_version, "ROOT", self.repo):
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(check_release_version.main([result.stdout.strip()]), 1)
                (self.repo / "package.json").write_text(json.dumps({"version": "2.12.30"}))
                self.assertEqual(check_release_version.main([result.stdout.strip()]), 0)

    def test_existing_but_unreachable_before_uses_main(self):
        self.git("checkout", "-b", "discarded", self.base)
        discarded = self.commit("discarded")
        self.git("checkout", "main")
        result = self.resolve(BEFORE=discarded)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), self.base)

    def test_new_branch_without_before_still_checks_the_delta(self):
        for before in ("", "0" * 40):
            with self.subTest(before=before):
                result = self.resolve(BEFORE=before)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), self.base)

    def test_pull_request_fetches_its_actual_base(self):
        result = self.resolve(EVENT_NAME="pull_request", BASE_REF="main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "origin/main")

    def test_failed_fallback_fetch_does_not_skip_validation(self):
        self.git("remote", "set-url", "origin", str(self.root / "missing.git"))
        result = self.resolve(BEFORE="f" * 40)
        self.assertNotEqual(result.returncode, 0)

    def test_unrelated_main_history_fails_closed(self):
        self.git("checkout", "--orphan", "unrelated")
        self.git("rm", "-f", "content.txt")
        self.commit("unrelated")
        result = self.resolve(BEFORE="f" * 40)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
