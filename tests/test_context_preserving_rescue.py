"""Regression checks for complete frames, names, and source-specific context."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rescue import rescue_text


class ContextPreservingRescue(unittest.TestCase):
    def test_complete_closing_frame_preserves_identifiers_and_conditions(self):
        for name in ("iOS", "eBay", "eBPF", "NASA", "the importer"):
            exposed = "The importer" if name == "the importer" else name
            source = f"In conclusion, {name} may accept 18 files only if the checksum matches."
            expected = f"{exposed} may accept 18 files only if the checksum matches."
            with self.subTest(name=name):
                self.assertEqual(rescue_text(source), expected)
                self.assertEqual(rescue_text(expected), expected)

    def test_closing_frame_leaves_quoted_code_and_incomplete_text_unchanged(self):
        for source in (
            'She wrote, "In conclusion, iOS may accept 18 files."',
            "`In conclusion, eBPF is supported.`",
            "```text\nIn conclusion, eBay is supported.\n```",
            "> In conclusion, the pilot may expand.",
            "The phrase in conclusion, remains part of the lesson.",
            "In conclusion,",
            "In conclusion, 東京 remains the export label.",
            "In conclusion, os.path.exists returned False.",
            "In conclusion, npm remains the installer.",
            "~~~text\nIn conclusion, eBPF is supported.\n~~~",
            "~~~~text\nIn conclusion, eBPF is supported.\n~~~\n~~~~",
            "~~~text\nIn conclusion, eBPF is supported.",
        ):
            with self.subTest(source=source):
                self.assertEqual(rescue_text(source), source)

    def test_generic_process_never_becomes_onboarding(self):
        source = ("The payroll exporter is a platform that leverages intelligent automation "
                  "to streamline the entire process end to end.")
        self.assertEqual(rescue_text(source),
                         "The payroll exporter is a platform that uses intelligent automation "
                         "to streamline the entire process.")

    def test_insights_never_become_conversations_or_an_invented_outcome(self):
        self.assertEqual(rescue_text("The insights were significant: the error affects only the pilot."),
                         "The insights were significant: the error affects only the pilot.")
        self.assertEqual(rescue_text("The insights were game-changing."), "The insights were useful.")


if __name__ == "__main__":
    unittest.main()
