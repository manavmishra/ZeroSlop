"""Guard the owner-confirmed hosted-service identity without changing legal rights."""
import pathlib
import unittest


class TermsOperatorTest(unittest.TestCase):
    def test_owner_confirmed_operator_is_used_consistently(self):
        terms = (pathlib.Path(__file__).resolve().parents[1] / "TERMS.md").read_text()
        self.assertNotIn("Garage Capital LLC", terms)
        self.assertEqual(terms.count("Garage Capital Ventures LLC"), 5)
        self.assertIn("Version 1.3", terms)
        self.assertIn("Effective 11 November 2026", terms)
        content = " ".join(terms.split("## 5. Your content stays yours", 1)[1].split("## 6.", 1)[0].split())
        self.assertIn("you authorise us to process that content solely to provide the requested service", content)
        self.assertIn("model providers described in Section 14", content)
        providers = " ".join(terms.split("## 14. Third-party services", 1)[1].split("## 15.", 1)[0].split())
        self.assertIn("Cloudflare Workers AI", providers)
        self.assertIn("OpenRouter to a free model provider", providers)
        self.assertIn("may keep the draft and the edit or use them to train models", providers)


if __name__ == "__main__":
    unittest.main()
