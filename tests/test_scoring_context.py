"""Source-aware prose measurement and length-independent vocabulary checks."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import slopscore


class ScoringContext(unittest.TestCase):
    def test_literal_fences_and_comments_do_not_create_phrase_findings(self):
        data = slopscore.load_patterns()
        prose = "The importer validates the request key before writing."
        control = slopscore.score_text(prose, data)
        for literal in (
            "~~~text\nIn conclusion, this is a game-changing journey.\n~~~",
            "~~~~text\n```\nIn conclusion, this is a game-changing journey.\n~~~~",
            "~~~text\nIn conclusion, this is a game-changing journey.",
            "<!-- In conclusion, this is a game-changing journey. -->",
        ):
            with self.subTest(literal=literal):
                measured = slopscore.score_text(prose + "\n\n" + literal, data)
                self.assertEqual(measured["hits"], control["hits"])
                self.assertEqual(measured["n_words"], control["n_words"])

    def test_a_different_fence_cannot_expose_literal_body(self):
        text = "~~~~text\n~~~\nIn conclusion, a game-changing journey.\n~~~~\nVisible prose."
        masked = slopscore._mask_fenced(text)
        self.assertNotIn("game-changing", masked)
        self.assertIn("Visible prose.", masked)

    def test_window_measurement_is_not_driven_by_total_document_length(self):
        cycle = [f"term-{index}" for index in range(200)]
        self.assertEqual(slopscore._windowed_word_variety(cycle * 5), 1.0)
        self.assertEqual(slopscore._windowed_word_variety(["same"] * 1000), .005)
        self.assertIsNone(slopscore._windowed_word_variety(cycle[:199]))

    def test_prose_emphasis_cannot_hide_tells_with_inline_backticks(self):
        data = slopscore.load_patterns()
        result = slopscore.score_text("We leveraged a `robust` `seamless` solution.", data)
        self.assertTrue(result["hits"])


if __name__ == "__main__":
    unittest.main()
