"""Offline submission metadata checks, not ChatGPT host certification.

Live endpoint evidence belongs in the private delivery packet. These checks
assert manifest requirements and source-bound cases without making API calls.
"""
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


class OpenAISubmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
        cls.interface = cls.manifest["interface"]
        cls.review = cls.manifest["extensions"]["com.openai"]["review"]
        cls.cases = cls.review["test_cases"]
        cls.contract = (ROOT / "mcp/gateway/src/contract.ts").read_text()
        cls.pipeline = (ROOT / "mcp/gateway/src/pipeline.ts").read_text()

    def test_required_manifest_and_interface_fields(self):
        for key in ("name", "version", "description", "author", "interface", "skills", "mcpServers"):
            self.assertTrue(self.manifest[key])
        self.assertTrue(self.manifest["author"]["name"])
        for key in ("displayName", "shortDescription", "longDescription", "developerName",
                    "category", "capabilities", "websiteURL", "supportURL", "privacyPolicyURL",
                    "termsOfServiceURL", "defaultPrompt", "composerIcon", "logo"):
            self.assertTrue(self.interface[key], key)
        self.assertEqual(self.manifest["skills"], "./skills/")

    def test_submission_character_limits(self):
        for key, maximum in (("displayName", 30), ("shortDescription", 30),
                             ("longDescription", 4000), ("developerName", 80)):
            self.assertIsInstance(self.interface[key], str)
            self.assertLessEqual(len(self.interface[key]), maximum, key)
        self.assertLessEqual(len(self.manifest["description"]), 4000)
        self.assertLessEqual(len(self.interface["capabilities"]), 20)
        for value in self.interface["capabilities"]:
            self.assertIsInstance(value, str)
            self.assertLessEqual(len(value), 120)

    def test_real_service_links_and_local_approved_icons(self):
        expected = {"websiteURL": "https://zero-slop.ai/",
                    "supportURL": "https://github.com/manavmishra/ZeroSlop/issues",
                    "privacyPolicyURL": "https://zero-slop.ai/privacy/",
                    "termsOfServiceURL": "https://zero-slop.ai/terms/"}
        for key, value in expected.items():
            self.assertEqual(self.interface[key], value)
            self.assertEqual(urlparse(value).scheme, "https")
        for key in ("composerIcon", "logo"):
            value = self.interface[key]
            self.assertTrue(value.startswith("./assets/logo/"))
            path = ROOT / value[2:]
            self.assertFalse(path.is_symlink())
            self.assertTrue(path.resolve().is_relative_to(ROOT.resolve()))
            self.assertTrue(path.is_file())
            self.assertLess(path.stat().st_size, 1024 * 1024)
            if path.suffix == ".svg":
                svg = ET.fromstring(path.read_bytes())
                self.assertEqual(svg.attrib["width"], svg.attrib["height"])
                self.assertGreaterEqual(int(svg.attrib["width"]), 128)

    def test_five_positive_and_three_negative_cases(self):
        self.assertEqual(len(self.cases["positive"]), 5)
        self.assertEqual(len(self.cases["negative"]), 3)
        descriptions = set()
        for kind, cases in self.cases.items():
            for case in cases:
                for key in ("description", "prompt", "expected_behavior"):
                    self.assertIsInstance(case[key], str)
                    self.assertTrue(case[key].strip())
                descriptions.add(case["description"])
                if kind == "positive":
                    self.assertEqual(case["tools_triggered"], "deslop")
                    self.assertIn("Call deslop", case["expected_behavior"])
                else:
                    self.assertNotIn("tools_triggered", case)
                    self.assertIn("not", case["expected_behavior"].lower())
                    self.assertIn("deslop", case["expected_behavior"])
        self.assertEqual(len(descriptions), 8)

    def test_review_does_not_require_dummy_or_unavailable_remote_artifacts(self):
        # example.com/brief is quoted draft data, never a demo or review link.
        for cases in self.cases.values():
            for case in cases:
                self.assertNotIn("file_attachment_urls", case)
                self.assertNotIn("expected_output_url", case)
                self.assertNotIn("https://", case["expected_behavior"])
        for key in self.review:
            self.assertNotIn(key, ("demo_url", "video_url", "demoURL", "videoURL"))
        self.assertFalse(self.review["commerce"])

    def test_positive_cases_are_bound_to_pipeline_behavior_and_source_details(self):
        genres = ("email", "professional", "email", "social", "research")
        for case, genre in zip(self.cases["positive"], genres):
            text = case["prompt"].split(": ", 1)[1]
            self.assertTrue(text.strip())
            self.assertLessEqual(len(text), 20_000)
            self.assertIn('"' + genre + '"', self.contract)
            self.assertIn(genre, case["expected_behavior"])
            self.assertRegex(case["expected_behavior"].lower(), r"unchanged|fallback|warning|failed checks|actual status")
        cases = self.cases["positive"]
        self.assertIn("already_clear", cases[0]["expected_behavior"])
        self.assertIn('original, "already_clear"', self.pipeline)
        self.assertIn("40%", cases[1]["prompt"])
        self.assertIn("Project Northstar", cases[1]["prompt"])
        self.assertIn('"Send the draft on Friday."', cases[2]["prompt"])
        self.assertIn("https://example.com/brief", cases[2]["prompt"])
        self.assertIn("product managers", cases[3]["prompt"])
        self.assertIn("24 participants", cases[4]["prompt"])
        self.assertIn("did not establish causation", cases[4]["prompt"])
        self.assertIn("Do not strengthen the causal claim", cases[4]["expected_behavior"])
        for status in ("already_clear", "unchanged_service_unavailable", "unchanged_verification_failed",
                       "rewritten", "rewritten_with_warnings"):
            self.assertIn('"' + status + '"', self.contract)
            self.assertIn('"' + status + '"', self.pipeline)
        for field in ("factsPreserved", "passedFinalChecks", "before", "after", "modelRequests", "note"):
            self.assertRegex(self.contract, r"\b" + re.escape(field) + r":")
        self.assertIn("429", self.contract)
        self.assertIn("capacity_limit", self.contract)
        self.assertIn("not a guarantee", self.interface["longDescription"])


if __name__ == "__main__":
    unittest.main()
