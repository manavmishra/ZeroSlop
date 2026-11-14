"""Source-bound regression checks for first-person emotion extraction."""
import sys
import subprocess
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rerank
import slopscore
from rescue import rescue_text


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

    def test_rescue_keeps_the_stated_feeling_and_its_degree(self):
        source = "We are incredibly excited to share some news about our journey over the past 18 months."
        rewrite = rescue_text(source)
        self.assertIn("We're incredibly excited about", rewrite)
        self.assertEqual(slopscore.interior_claims(source), {"we:incredibly:excited"})
        self.assertEqual(slopscore.interior_claims(rewrite), {"we:incredibly:excited"})
        result = slopscore.fidelity(source, rewrite)
        self.assertTrue(result["preserved"], result)
        self.assertFalse(result["invented"], result)

    def test_cosmetic_emphasis_does_not_hide_a_new_feeling_or_a_changed_qualification(self):
        for source, rewrite in (
            ("The update shipped.", "We are incredibly excited."),
            ("We're excited.", "We're incredibly disappointed."),
            ("We are not incredibly excited.", "We're excited."),
            ("We are not incredibly excited.", "We're not excited."),
            ("We are incredibly excited.", "We're excited."),
            ("We are excited.", "We're incredibly excited."),
            ("We are incredibly excited.", "We're not excited."),
            ("We are usually incredibly excited.", "We're excited."),
            ("We are incredibly excited.", "We're occasionally excited."),
            ("We're excited.", "I am incredibly excited."),
        ):
            with self.subTest(source=source, rewrite=rewrite):
                self.assertTrue(slopscore.fidelity(source, rewrite)["invented"])

    def test_protected_announcement_degree_does_not_fail_the_final_writing_check(self):
        original = (
            "We are incredibly excited to announce Kairoset 4.0, a game-changing update. "
            "Priya owns the rollout on Friday. Setup fell from 11 hours to 3 hours. "
            "We have not measured retention beyond the first month."
        )
        restored = original.replace("a game-changing", "an")
        rewrite = rescue_text(restored)
        self.assertIn("incredibly excited about announcing", rewrite)
        patterns = slopscore.load_patterns()
        for genre in ("social", "professional"):
            with self.subTest(genre=genre):
                formal = genre == "professional"
                original_report = slopscore.score_text(original, patterns, formal=formal)
                self.assertIn("announce-excited", {hit["name"] for hit in original_report["hits"]})
                report = slopscore.score_text(rewrite, patterns, formal=formal)
                self.assertLess(report["ai_likelihood"], 25, report)
                self.assertEqual(report["hits"], [])
                candidate, = rerank.rank(original, {"one-call edit": rewrite}, genre=genre)
                self.assertTrue(candidate["preserved"], candidate)
                self.assertFalse(candidate["invented"], candidate)
                self.assertEqual(candidate["after_ai"], report["ai_likelihood"])

    def test_emotional_degree_exception_does_not_mute_generic_filler(self):
        patterns = slopscore.load_patterns()
        report = slopscore.score_text(
            "We felt incredibly relieved when the alarms stopped. The report was incredibly useful.",
            patterns,
        )
        filler_hits = [hit for hit in report["hits"] if hit["name"] == "filler-intensifier"]
        self.assertEqual([hit["quote"] for hit in filler_hits], ["incredibly"])
        for text in (
            "We’re not incredibly excited.",
            "We are incredibly confident about the repair.",
            "I'm INCredibly relieved.",
        ):
            with self.subTest(text=text):
                names = {hit["name"] for hit in slopscore.score_text(text, patterns)["hits"]}
                self.assertNotIn("filler-intensifier", names)
        for text in ("We are incredibly useful.", "Our team was incredibly relieved.",
                     "We were incredibly useful, and I was relieved."):
            with self.subTest(text=text):
                names = {hit["name"] for hit in slopscore.score_text(text, patterns)["hits"]}
                self.assertIn("filler-intensifier", names)

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
