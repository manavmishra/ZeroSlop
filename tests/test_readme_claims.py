"""Keep the README's external ranking and measured reach within their evidence."""

from pathlib import Path
import unittest


README = Path(__file__).resolve().parents[1] / "README.md"


class ReadmeClaims(unittest.TestCase):
    def setUp(self):
        self.introduction = README.read_text().split("## Context-preserving edits", 1)[0]

    def test_ranking_names_the_review_and_its_test_scope(self):
        self.assertIn("Ranked #2 for finding and fixing AI slop.", self.introduction)
        self.assertIn(
            "[Read the review](https://growthmethod.com/ai-writing-skills-avoid-slop/#2-zero-slop)",
            self.introduction,
        )
        self.assertRegex(self.introduction, r"ten skills.*one article.*AI judges")
        self.assertNotRegex(self.introduction, r"(?i)#2 (?:on the internet|worldwide|of 73)")

    def test_worldwide_reach_is_dated_network_activity_not_a_user_count(self):
        self.assertIn("82 countries and territories", self.introduction)
        self.assertIn("November 23, 2026", self.introduction)
        self.assertIn("network activity", self.introduction)
        self.assertIn("may include automation", self.introduction)
        self.assertIn("https://zero-slop.ai/press/measurement-notes/", self.introduction)
        self.assertNotRegex(self.introduction, r"(?i)(?:25[,.]?0*\s*k?|82)\s+(?:unique\s+)?users")

    def test_mcp_remains_a_direct_intro_access_path(self):
        self.assertIn("[MCP connector](https://mcp.zero-slop.ai/mcp)", self.introduction)


if __name__ == "__main__":
    unittest.main()
