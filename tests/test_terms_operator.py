"""Guard the owner-confirmed hosted-service identity without changing legal rights."""
import pathlib
import unittest


class TermsOperatorTest(unittest.TestCase):
    def test_owner_confirmed_operator_is_used_consistently(self):
        terms = (pathlib.Path(__file__).resolve().parents[1] / "TERMS.md").read_text()
        self.assertNotIn("Garage Capital LLC", terms)
        self.assertEqual(terms.count("Garage Capital Ventures LLC"), 5)
        self.assertIn("Version 1.1", terms)
        self.assertIn("Operator name corrected", terms)


if __name__ == "__main__":
    unittest.main()
