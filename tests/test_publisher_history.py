"""Publisher checkouts must include the pinned history used by release tests."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class PublisherHistoryTests(unittest.TestCase):
    def test_test_bearing_publishers_fetch_complete_history(self):
        for name in ("publish-npm.yml", "release-on-tag.yml"):
            with self.subTest(workflow=name):
                source = (ROOT / ".github" / "workflows" / name).read_text()
                # Restrict the assertion to the first checkout's own inputs;
                # a later job or unrelated step cannot satisfy this contract.
                first_checkout = re.search(
                    r"(?m)^      - uses: actions/checkout@[^\n]+\n"
                    r"(?P<inputs>(?:(?!      - ).*\n)*)", source)
                self.assertIsNotNone(first_checkout)
                self.assertRegex(first_checkout.group("inputs"),
                                 r"(?m)^          fetch-depth: 0$")
                self.assertIn("python3 -m unittest discover -s tests", source)
                self.assertLess(source.index("publication_guard.py"),
                                source.index("python3 -m unittest discover -s tests"))


if __name__ == "__main__":
    unittest.main()
