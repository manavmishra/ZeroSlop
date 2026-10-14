"""Offline fallback regression for the fictional hosted Northstar incident."""
import sys
import subprocess
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rescue
import slopscore


SOURCE = (
    "We’re thrilled to announce a game-changing update to Project Northstar. "
    "Starting October 20, teams can export their weekly report as a CSV file. "
    "It is important to note that Maya owns the rollout, and the beta is limited to 25 teams. "
    "This seamless experience empowers teams to unlock actionable insights."
)
EXPECTED = (
    "We’re thrilled to announce an update to Project Northstar. "
    "Starting October 20, teams can export their weekly report as a CSV file. "
    "Maya owns the rollout, and the beta is limited to 25 teams. "
    "This seamless experience empowers teams to unlock actionable insights."
)


class NorthstarRescue(unittest.TestCase):
    def test_exact_incident_keeps_emotion_and_benefit_without_cosmetic_paraphrase(self):
        self.assertEqual(rescue.rescue_text(SOURCE), EXPECTED)
        self.assertEqual(rescue.rescue_text(EXPECTED), EXPECTED)
        checked = slopscore.fidelity(SOURCE, EXPECTED)
        self.assertTrue(checked["preserved"])
        self.assertFalse(checked["invented"])
        self.assertIn("thrilled to announce", EXPECTED)
        self.assertIn("This seamless experience empowers teams to unlock actionable insights.", EXPECTED)
        self.assertNotIn("useful update", EXPECTED)
        self.assertNotIn("excited about", EXPECTED)

    def test_present_announcement_keeps_emotion_subject_and_noun(self):
        for verb in ("’re", "'re", " are"):
            for noun in ("an update to iOS", "a release for eBay and NASA"):
                source = f"We{verb} thrilled to announce {noun}."
                expected = f"We{verb} thrilled to announce {noun}."
                self.assertEqual(rescue.rescue_text(source), expected)

    def test_benefit_keeps_agent_and_claim_instead_of_deleting_sentence(self):
        for agent in ("teams", "users", "people"):
            source = f"This seamless experience empowers {agent} to unlock actionable insights."
            expected = source
            self.assertEqual(rescue.rescue_text(source), expected)

    def test_quotations_code_and_links_are_byte_preserved(self):
        for protected in (
            f'"{SOURCE}"', f"“{SOURCE}”", f"‘{SOURCE}’", f"'{SOURCE}'",
            "'We're thrilled to announce a game-changing update to Project Northstar.'",
            f"`{SOURCE}`", f"```text\n{SOURCE}\n```", f"> {SOURCE}",
            f"[We’re thrilled to announce](https://example.test/{'game-changing-update'})",
            "https://example.test/seamless-experience?owner=Maya&teams=25",
        ):
            with self.subTest(protected=protected):
                self.assertEqual(rescue.rescue_text(protected), protected)
                self.assertEqual(rescue.rescue_text(SOURCE + "\n\n" + protected),
                                 EXPECTED + "\n\n" + protected)

    def test_negation_certainty_timing_and_named_terms_survive(self):
        claim = ("Maya may not approve the rollout before October 20. "
                 "iOS and eBay cannot export CSV; NASA will not join the 25-team beta.")
        self.assertEqual(rescue.rescue_text(SOURCE + " " + claim), EXPECTED + " " + claim)
        for source in (
            "We are not thrilled to announce an update to iOS.",
            "We were thrilled to announce an update to iOS.",
            "Maya said we are thrilled to announce an update to iOS.",
            "We are thrilled to announce that the beta may not launch.",
            "This experience does not empower teams to find insights.",
            "This seamless experience may empower teams to unlock actionable insights.",
            "This seamless experience empowers teams to unlock actionable insights only after approval.",
            "This Seamless Experience empowers teams to unlock actionable insights.",
            "The report shows 25 teams can export CSV on October 20.",
        ):
            with self.subTest(source=source):
                self.assertEqual(rescue.rescue_text(source), source)

    def test_complete_multiline_quotations_preserve_internal_apostrophes(self):
        for opening, closing in (("“", "”"), ("‘", "’"), ('"', '"'), ("'", "'")):
            for verb in ("’re", "'re"):
                quoted = (opening + "Maya said:\n\nWe" + verb
                          + " thrilled to announce an update to Project Northstar.\n"
                          + "This seamless experience empowers teams to unlock actionable insights.\n"
                          + closing)
                with self.subTest(opening=opening, verb=verb):
                    self.assertEqual(rescue.rescue_text(quoted), quoted)
                    self.assertEqual(rescue.rescue_text(SOURCE + "\n\n" + quoted),
                                     EXPECTED + "\n\n" + quoted)

    def test_unmatched_quote_flood_completes_within_bounded_cli_time(self):
        # One MiB of repeated unmatched openers previously made the quote
        # regex rescan almost the entire remaining input at every line.
        flood = "‘\n" * 262144
        quoted = "“Maya said:\n\n" + SOURCE + "\n”"
        text = flood + quoted + "\n\n" + SOURCE
        result = subprocess.run(
            [sys.executable, str(Path(rescue.__file__)), "-"],
            input=text, capture_output=True, text=True, timeout=5, check=True,
        )
        self.assertEqual(result.stdout, text + "\n")

    def test_unmatched_quotations_abstain_from_editing_the_suffix(self):
        for opener in ('"', "'", "“", "‘"):
            quoted = opener + "Maya said:\n\n" + SOURCE
            self.assertEqual(rescue.rescue_text(quoted), quoted)
            self.assertEqual(rescue.rescue_text(SOURCE + "\n\n" + quoted),
                             EXPECTED + "\n\n" + quoted)

    def test_nested_quotations_and_protected_inner_spans_remain_exact(self):
        for quoted in (
            '“Maya said \'We\'re thrilled to announce an update.\'\n' + SOURCE + '”',
            '"Maya said:\nhttps://example.test/\n`game-changing`\n' + SOURCE + '"',
            "‘Maya said:\n\nWe're thrilled to announce an update.\n" + SOURCE + "’",
            '"Maya said: `"`\n\n' + SOURCE + '\n"',
            '"Maya said: [a "label"](https://example.test/)\n\n' + SOURCE + '\n"',
            '“Maya said:\n\n' + SOURCE + '\nhttps://example.test/”.',
            '"Maya said:\n\n' + SOURCE + '\nhttps://example.test/".',
        ):
            self.assertEqual(rescue.rescue_text(quoted), quoted)


if __name__ == "__main__":
    unittest.main()
