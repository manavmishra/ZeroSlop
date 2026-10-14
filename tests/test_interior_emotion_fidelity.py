"""Source-bound regression checks for first-person emotion extraction."""
import sys
import subprocess
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import slopscore


SOURCE = (
    "We’re thrilled to announce a game-changing update to Project Northstar. "
    "Starting October 20, teams can export their weekly report as a CSV file. "
    "It is important to note that Maya owns the rollout, and the beta is limited to 25 teams. "
    "This seamless experience empowers teams to unlock actionable insights."
)
PARAPHRASE = (
    "We feel thrilled about the update to Project Northstar. "
    "Starting October 20, teams can export their weekly report as a CSV file. "
    "Maya owns the rollout, and the beta is limited to 25 teams. "
    "This seamless experience empowers teams to unlock actionable insights."
)


class InteriorEmotionFidelity(unittest.TestCase):
    def test_exact_fictional_paraphrase_keeps_stated_feeling(self):
        result = slopscore.fidelity(SOURCE, PARAPHRASE)
        self.assertTrue(result["preserved"], result)
        self.assertFalse(result["invented"], result)
        self.assertFalse(result["interior"], result)

    def test_full_and_contracted_forms_share_only_the_same_speaker_state(self):
        for variants, feeling in (
            (("We're thrilled.", "We’re thrilled.", "We are thrilled.", "We were thrilled.",
              "We feel thrilled.", "We felt thrilled."), "thrilled"),
            (("I'm nervous.", "I’m nervous.", "I am nervous.", "I was nervous.",
              "I feel nervous.", "I felt nervous."), "nervous"),
        ):
            for source in variants:
                for rewrite in variants:
                    with self.subTest(source=source, rewrite=rewrite):
                        self.assertEqual(slopscore.interior_claims(source),
                                         slopscore.interior_claims(rewrite))
                        self.assertFalse(slopscore.fidelity(source, rewrite)["invented"])

    def test_new_positive_negative_and_qualified_feelings_remain_inventions(self):
        for rewrite in ("We're thrilled.", "We’re not thrilled.", "We are not thrilled.",
                        "We aren't thrilled.", "I'm nervous.", "I’m slightly nervous.",
                        "We feel somewhat relieved.", "We are terrified."):
            with self.subTest(rewrite=rewrite):
                self.assertTrue(slopscore.fidelity("The update shipped.", rewrite)["invented"])

    def test_speaker_transfer_remains_rejected(self):
        for source, rewrite in (
            ("We’re thrilled.", "I feel thrilled."),
            ("We are thrilled.", "I am thrilled."),
            ("I'm nervous.", "We feel nervous."),
        ):
            self.assertTrue(slopscore.fidelity(source, rewrite)["invented"])

    def test_negation_and_meaningful_degree_do_not_license_unqualified_emotion(self):
        for source in ("We're not thrilled.", "We’re never thrilled.", "We aren't thrilled.",
                       "We are somewhat thrilled.", "We’re barely thrilled.",
                       "We feel slightly thrilled.", "We’re probably thrilled."):
            with self.subTest(source=source):
                self.assertTrue(slopscore.fidelity(source, "We feel thrilled.")["invented"])
                self.assertFalse(slopscore.fidelity(source, source)["invented"])

    def test_conditional_modal_wish_and_attributed_states_do_not_license_assertion(self):
        for source in (
            "If the beta launches, we're thrilled.",
            "We're thrilled if the beta launches.",
            "We might be thrilled.", "We may be thrilled.",
            "I wish we were thrilled.", "Maya said we are thrilled.",
            'Maya said, "We’re thrilled."',
            'Maya said:\n\n“We’re thrilled.\n”',
            "Maya said, ‘We're thrilled.’", "Maya said, 'We're thrilled.'",
            "> We're thrilled.",
        ):
            with self.subTest(source=source):
                self.assertTrue(slopscore.fidelity(source, "We feel thrilled.")["invented"])

    def test_quote_or_condition_preserved_does_not_license_added_writer_feeling(self):
        for source in ('Maya said, "We’re thrilled."',
                       "We’re thrilled if the beta launches."):
            self.assertTrue(slopscore.fidelity(source, source + " We feel thrilled.")["invented"])

    def test_non_emotional_copula_activities_are_not_new_feeling_assertions(self):
        for text in ("We're exporting CSV.", "We are exporting CSV.",
                     "I'm building the importer.", "We are product managers."):
            with self.subTest(text=text):
                self.assertFalse(slopscore.interior_claims(text))

    def test_long_context_and_unmatched_quote_flood_have_bounded_work(self):
        # Repeating states within one qualified sentence must not repeatedly
        # normalize/copy the entire sentence tail. Unmatched openers likewise
        # must use a forward scan rather than a regex suffix search.
        runner = ("import sys;sys.path.insert(0,sys.argv[1]);import slopscore;"
                  "states=slopscore.interior_claims(sys.stdin.read());"
                  "print(len(states));print(max(map(len,states),default=0))")
        for text in (
            "Maya said, if the beta launches, " + "We're thrilled, " * 32768,
            "‘\n" * 131072 + "We're thrilled.",
        ):
            result = subprocess.run(
                [sys.executable, "-c", runner, str(Path(slopscore.__file__).parent)],
                input=text, text=True, capture_output=True, timeout=5, check=True,
            )
            count, longest = map(int, result.stdout.splitlines())
            self.assertEqual(count, 1)
            self.assertLess(longest, 100, "context keys retain a bounded fingerprint, not draft text")


if __name__ == "__main__":
    unittest.main()
