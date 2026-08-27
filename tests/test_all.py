#!/usr/bin/env python3
"""End-to-end suite: detector, reflect loop, safety gates, decay, scale.

    python3 tests/test_all.py           # everything
    python3 tests/test_all.py -v        # per-test detail
    python3 tests/test_all.py Scale     # one class

Stdlib unittest, no dependencies, no network — a contributor with a bare Python
can verify the whole thing. Tests that write data operate on a temp copy of
data/ so a failing run can never corrupt the shipped taxonomy.
"""
import json
import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
DATA = ROOT / "data"
CORPUS = DATA / "corpus" / "must-not-flag"
SCORER = ROOT / "scripts" / "slopscore.py"
LEARNER = ROOT / "scripts" / "learn.py"
CONTEXTUAL = ROOT / "scripts" / "contextual.py"
QUALITY_EVAL = ROOT / "bench" / "quality-corpus" / "evaluate.py"
QUALITY_PACKET = ROOT / "bench" / "quality-corpus" / "make_packet.py"
QUALITY_ROOT = ROOT / "bench" / "quality-corpus"
QUALITY_BUILD = QUALITY_ROOT / "build_manifest.py"
CORPUS_REGISTRY = ROOT / "bench" / "validate_corpus_registry.py"
FEATURE_ABLATION = ROOT / "bench" / "feature-ablation" / "check.py"

import learn  # noqa: E402
import slopscore  # noqa: E402


def run(args, stdin=None, env=None):
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, input=stdin, cwd=str(ROOT), env=env)


def score(text):
    """Heuristic surface score for a string, via the library path."""
    data = slopscore.load_patterns()
    return slopscore.score_text(text, data)["ai_likelihood"]


# --------------------------------------------------------------------------
class Taxonomy(unittest.TestCase):
    """The pattern database itself has to be well-formed to be trustworthy."""

    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((DATA / "patterns.json").read_text())
        cls.learned = json.loads((DATA / "learned.json").read_text())
        cls.all = cls.base["patterns"] + cls.learned.get("patterns", [])

    def test_every_regex_compiles(self):
        for p in self.all:
            with self.subTest(p["name"]):
                re.compile(p["rx"])

    def test_no_duplicate_names(self):
        names = [p["name"] for p in self.all]
        self.assertEqual(len(names), len(set(names)),
                         f"duplicates: {[n for n in names if names.count(n) > 1]}")

    def test_every_pattern_is_dated(self):
        """Provenance is what makes decay possible; undated patterns never age."""
        undated = [p["name"] for p in self.all if not p.get("first_seen")]
        self.assertEqual(undated, [], f"undated patterns are invisible to decay: {undated}")

    def test_weights_in_range(self):
        for p in self.all:
            self.assertTrue(0 < p["w"] <= 10, f"{p['name']} weight {p['w']}")

    def test_learned_cannot_override_base(self):
        """Documented contract: learned patterns append, they never shadow base."""
        base_names = {p["name"] for p in self.base["patterns"]}
        clash = [p["name"] for p in self.learned.get("patterns", [])
                 if p["name"] in base_names]
        self.assertEqual(clash, [], f"learned shadows base: {clash}")


# --------------------------------------------------------------------------
class Detector(unittest.TestCase):
    """Does the meter separate machine register from honest human writing?"""

    SLOP = ("🚀 I'm beyond excited to announce that we've raised our seed round "
            "to revolutionize how teams ship software! This wasn't just a "
            "milestone — it's a testament to our incredible team. Let's dive "
            "into the 3 key lessons. It's worth noting that we leveraged "
            "cutting-edge solutions to seamlessly elevate our robust platform "
            "and unlock unprecedented value. Agree? 👇 #Startup #AI")

    def test_flags_obvious_slop(self):
        self.assertGreater(score(self.SLOP), 70)

    def test_v23_tell_families_are_caught(self):
        """The 2026-08 expansion: each family's canonical form must draw at
        least one pattern hit. These were audited as 0-hit misses before
        v2.3.0 — the contrast family was contraction- and separator-locked,
        and whole families (fake epiphany, certainty theater, cliché
        autopilot, chatbot residue) had no regex at all."""
        data = slopscore.load_patterns()
        canonical = [
            "Success isn't about talent. It's about consistency.",
            "It's not just a tool—it's a partner.",
            "It is not about speed; it is about direction.",
            "It's less about the code and more about the culture.",
            "We didn't just build a product. We built a movement.",
            "Stop chasing followers. Start building trust.",
            "Gone are the days of manual deploys.",
            "In a world where attention is currency, silence is strategy.",
            "That's when it hit me.",
            "The importance of onboarding cannot be overstated.",
            "Only time will tell.",
            "AI is a double-edged sword, and that's just the tip of the iceberg.",
            "Would you like me to draft that for you?",
            "This is your sign to take the leap.",
            "The best part? It runs offline.",
        ]
        for s in canonical:
            with self.subTest(s[:40]):
                hits = [h for h in slopscore.score_text(s, data)["hits"]
                        if h["cat"] not in ("lexicon", "rider")]
                self.assertTrue(hits, f"no pattern hit on: {s!r}")

    UNMARKED_ANTITHESIS = [
        # isocolon: one verb frame, both arguments swapped, no negation marker
        ("Open weights let you adapt a model. An open stack lets you adapt "
         "the machinery that created it.", "isocolon-ditransitive"),
        ("Most AI-writing tools hand you a verdict. The slop score hands you "
         "arithmetic.", "isocolon-ditransitive"),
        ("The old plan gives you a number. The new one gives you a reason.",
         "isocolon-ditransitive"),
        # the stock closer
        ("Ai2 argues for full openness as a principle. This is what that "
         "principle looks like when it works.", "this-is-what-looks-like"),
        # unmarked reversal — 'No X had to …; Y did'
        ("No frontier lab had to decide the language was worth prioritizing. "
         "Local researchers made that decision themselves.", "no-x-had-to"),
        # significance scaffolding, one word outside the old closed noun set
        ("Here's the detail that matters: the pipeline was open too.",
         "performed-candor"),
    ]

    def test_unmarked_antithesis_is_caught(self):
        """v2.5.10. Every 'contrast' pattern used to require a literal negation
        token, so the same figure with no marker scored clean — four of them in
        209 words returned 13.0/100. Each shape here must draw its own pattern."""
        data = slopscore.load_patterns()
        for text, expected in self.UNMARKED_ANTITHESIS:
            with self.subTest(expected):
                names = {h["name"] for h in slopscore.score_text(text, data)["hits"]}
                self.assertIn(expected, names,
                              f"{expected} did not fire on: {text!r}")

    def test_isocolon_rule_turns_on_verb_identity(self):
        """The safety property, pinned. `isocolon-ditransitive` fires only when
        the SAME verb repeats across the sentence break. Rhetorical anaphora
        repeats its frame with a different verb every time, which is exactly why
        the rule cannot reach Gettysburg. Relaxing the backreference from the
        verb to the frame was measured firing on gettysburg.txt, federalist.txt
        and esl-engineer-email.txt. If this test fails, the rule was loosened."""
        data = slopscore.load_patterns()
        # different verb in the same frame -> must stay silent
        for safe in ("This one gives you a number. That one hands you a reason.",
                     "The first shows you the score. The second tells you why."):
            with self.subTest(safe[:40]):
                names = {h["name"] for h in slopscore.score_text(safe, data)["hits"]}
                self.assertNotIn("isocolon-ditransitive", names,
                                 "isocolon rule fired on a different-verb pair; "
                                 "the backreference was relaxed off the verb")

    def test_performed_register_corpus_is_caught(self):
        """The 2026-08-24 expansion: performed-writer prose, an AI imitating a
        punchy human writer. Every span in the mechanical half of the corpus
        was a human-editor-flagged miss that scored clean before v2.5.6; each
        must keep drawing at least one pattern hit. The judgment half is
        documented as regex-uncatchable in the corpus README and is not
        asserted here."""
        data = slopscore.load_patterns()
        mech = DATA / "corpus" / "performed-register" / "mechanical"
        files = sorted(mech.glob("*.txt"))
        self.assertGreaterEqual(len(files), 16, "mechanical corpus went missing")
        for f in files:
            with self.subTest(f.name):
                hits = [h for h in slopscore.score_text(f.read_text(), data)["hits"]
                        if h["cat"] not in ("lexicon", "rider")]
                self.assertTrue(hits, f"performed-register regression: {f.name} "
                                      f"draws no pattern hit")

    def test_human_corpus_stays_clean(self):
        """The false-positive floor. Every one of these is real human writing."""
        for f in sorted(CORPUS.glob("*.txt")):
            with self.subTest(f.name):
                self.assertLess(score(f.read_text()), 30,
                                f"{f.name} convicted as AI")

    def test_human_technical_prose_is_not_convicted(self):
        """Ordinary human docs in this repo must clear the gate.

        A corroboration floor of 0.45 plus a clamp keyed on hit *count* meant one
        weight-2.5 tell in 392 words scored AGENTS.md at 59.2. Five of eight
        human-written documents were convicted. Files that deliberately carry
        slop specimens (rewrite-moves, overcorrection, evidence) are excluded —
        their score is use/mention, not a false positive.
        """
        for name in ("AGENTS.md", "SECURITY.md"):
            with self.subTest(name):
                s = score((ROOT / name).read_text())
                self.assertLess(s, 25, f"{name} convicted at {s}")

    def test_a_single_light_tell_cannot_convict(self):
        """One weak hit is not a cluster, and clusters are what convict."""
        plain = (
            "The service reads from the queue and writes to the primary. "
            "Configuration lives in the deploy repo under env/, which is where "
            "the on-call rotation looks first when something is misbehaving at "
            "two in the morning and nobody remembers who changed what. "
            "Rollback is one command. It takes under a minute, assuming the "
            "migration was reversible, and about half of ours are not. "
            "The runbook covers the three alerts that actually page someone; "
            "everything else goes to a channel that people read when they can. "
            "Nobody has updated the section on the old billing job since we "
            "moved it off cron, which is a problem waiting to happen.")
        with_arrow = plain + " The flow is read \u2192 transform \u2192 write."
        self.assertLess(score(with_arrow), 25,
                        "one spec-notation hit unlocked the stylistic penalty")

    def test_idempotence(self):
        """Clean text must survive re-scoring unchanged — the skill promises this."""
        clean = (CORPUS / "terse-engineer-note.txt").read_text()
        a, b = score(clean), score(clean)
        self.assertEqual(a, b)

    def test_empty_and_tiny_input(self):
        for t in ["", " ", "Hi.", "\n\n\n"]:
            with self.subTest(repr(t)):
                s = score(t)
                self.assertGreaterEqual(s, 0)
                self.assertLessEqual(s, 100)

    def test_empty_input_reports_zero_words(self):
        result = slopscore.score_text("", slopscore.load_patterns())
        self.assertEqual(result["n_words"], 0)

    def test_formal_mode_relaxes_register(self):
        """Research register is native in a journal abstract, not a tell."""
        abstract = ((CORPUS / "ml-methods.txt").read_text())
        data = slopscore.load_patterns()
        plain = slopscore.score_text(abstract, data)["ai_likelihood"]
        formal = slopscore.score_text(abstract, data, formal=True)["ai_likelihood"]
        self.assertLessEqual(formal, plain)

    def test_backtick_code_is_not_laundering(self):
        """Wrapping a tell in backticks must not hide it from the meter."""
        bare = "We leveraged a robust seamless solution to elevate the platform."
        ticked = "We leveraged a `robust` `seamless` solution to elevate the platform."
        self.assertGreater(score(ticked), score(bare) * 0.5)

    def test_community_research_does_not_turn_single_style_choices_into_verdicts(self):
        """The Reddit study ranks reader complaints; it is not a licence to
        ban punctuation or ordinary connective words. Corroboration still wins."""
        samples = [
            "The deploy failed—again—because the migration held the lock.",
            "However, the second run completed after the lock expired.",
            "Thus the recorded total remains comprehensive enough for this audit.",
        ]
        for text in samples:
            with self.subTest(text=text):
                self.assertLess(score(text), 30)

    def test_generic_benefit_stacks_need_a_specific_claim(self):
        """A product noun plus two generic outcomes is a corroborated cluster,
        not a banned word. Concrete capabilities and measured results stay
        clean; interchangeable sales copy crosses the writing gate."""
        vague = [
            ("Our platform can help your team work together and create more "
             "value. Would you be open to discussing how we might work together?"),
            ("We are launching a solution designed to change how your organization "
             "works. It offers an easier experience, strong capabilities, and "
             "greater efficiency."),
        ]
        grounded = [
            ("The service helps the billing team reconcile invoices and cut the "
             "month-end run from four hours to 35 minutes."),
            "The platform offers CSV export, SAML SSO, and 99.95% uptime.",
        ]
        for text in vague:
            with self.subTest(kind="vague", text=text):
                self.assertGreaterEqual(score(text), 25)
        for text in grounded:
            with self.subTest(kind="grounded", text=text):
                self.assertLess(score(text), 25)

    def test_optimized_lexicon_scan_matches_the_reference_algorithm(self):
        """The fast scanner must preserve every old match, including awkward
        overlapping stems and private multiword terms. Performance is never a
        licence to move a score or relabel a hit."""
        lexicon = {
            "game-chang": 5,
            "game-changing": 7,
            "foo": 1,
            "foo-bar": 2,
            "fight against": 3,
            "İdea": 2,
            "ßeta": 2,
            "unused": 0,
        }
        texts = [
            "A game-changing idea is not a game-changer.",
            "foo foo-bar foobar; we fight against waste.",
            "FOO-BAR and Game-Changing, then unused.",
            "prefixfoo must stay silent; foo2 must count.",
            "idea and ßeta exercise Unicode case-folding boundaries.",
        ]

        def reference(text):
            found = []
            for order, (term, weight) in enumerate(lexicon.items()):
                if not weight:
                    continue
                for match in re.finditer(r"\b" + re.escape(term) + r"\w*", text, re.I):
                    found.append((match.start(), match.end(), order, term, weight,
                                  match.group(0).lower()))
            found.sort(key=lambda row: (row[0], -row[1], row[2]))
            return [(start, end, term, weight, quote)
                    for start, end, _, term, weight, quote in found]

        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(
                    slopscore._term_candidates(text, lexicon),
                    reference(text),
                )

    def test_model_tracking_url_artifact_survives_url_stripping(self):
        data = slopscore.load_patterns()
        text = "Source: https://example.com/paper?utm_source=chatgpt.com"
        hits = slopscore.score_text(text, data)["hits"]
        self.assertTrue(any(h["name"] == "chatgpt-artifact" for h in hits))

    def test_ordinary_url_remains_noise(self):
        data = slopscore.load_patterns()
        plain = slopscore.score_text("Source:", data)
        linked = slopscore.score_text(
            "Source: https://example.com/robust-seamless-tapestry", data
        )
        self.assertEqual(plain["hits"], linked["hits"])

    def test_attributable_index_artifact_is_caught(self):
        data = slopscore.load_patterns()
        text = '<span data-attributableIndex="12">The museum opened.</span>'
        hits = slopscore.score_text(text, data)["hits"]
        self.assertTrue(any(h["name"] == "chatgpt-artifact" for h in hits))

    def test_export_placeholders_are_caught(self):
        data = slopscore.load_patterns()
        text = "Dear [Recipient], join [Company Name] on [Date]."
        hits = slopscore.score_text(text, data)["hits"]
        placeholders = [h for h in hits if h["name"] == "placeholder"]
        self.assertEqual(len(placeholders), 3)

    def test_regenerate_response_ui_leak_is_caught(self):
        data = slopscore.load_patterns()
        hits = slopscore.score_text("Regenerate response", data)["hits"]
        self.assertTrue(any(
            h["name"] == "regenerate-response-artifact" for h in hits
        ))


# --------------------------------------------------------------------------
class CLI(unittest.TestCase):
    """Exit codes and output contracts other tools depend on."""

    def test_gate_passes_clean_text(self):
        r = run([str(SCORER), "--gate", "25", str(CORPUS / "terse-engineer-note.txt")])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_gate_fails_slop_with_exit_1(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(Detector.SLOP)
            p = f.name
        r = run([str(SCORER), "--gate", "25", p])
        self.assertEqual(r.returncode, 1)
        Path(p).unlink()

    def test_json_is_valid_and_has_contract_keys(self):
        r = run([str(SCORER), "--json", str(CORPUS / "gettysburg.txt")])
        d = json.loads(r.stdout)
        for k in ("score_kind", "calibrated_probability", "ai_likelihood",
                  "burstiness", "n_words", "hits"):
            self.assertIn(k, d)
        self.assertEqual(d["score_kind"], "heuristic_surface_meter")
        self.assertFalse(d["calibrated_probability"])

    def test_reads_stdin(self):
        r = run([str(SCORER)], stdin="A short honest sentence about nothing.")
        self.assertIn("Writing score", r.stdout)

    def test_human_report_uses_plain_language(self):
        """Normal output is written for a writer, not the scoring code."""
        r = run([str(SCORER), "--explain"], stdin=Detector.SLOP)
        self.assertEqual(r.returncode, 0, r.stderr)
        for phrase in (
                "Writing score", "Flagged phrases", "Sentence variety",
                "Readability", "What Zero Slop checked", "Your AI assistant"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), r.stdout.lower())
        for term in (
                "surface score", "heuristic meter", "tell density",
                "weighted tells", "burstiness", "followability", "evidence",
                "heatmap", "scorecard", "fidelity", "register", "artifact",
                "candidate", "overlay", "corpus", "diagnostic"):
            with self.subTest(term=term):
                self.assertNotIn(term, r.stdout.lower())

    def test_unicode_does_not_crash(self):
        r = run([str(SCORER)], stdin="Ünïcödé — emoji 🚀 中文 العربية\n")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_zero_width_obfuscation_cannot_hide_a_known_term(self):
        """Invisible characters may arrive through paste, but they cannot turn
        a known phrase into a clean one."""
        data = slopscore.load_patterns()
        result = slopscore.score_text(
            "We should del\u200bve into the intricate tapestry before launch.", data
        )
        names = {hit["name"] for hit in result["hits"]}
        self.assertIn("delve", names)
        self.assertEqual(result["normalization"]["zero_width"], 1)

    def test_mixed_script_obfuscation_cannot_hide_a_known_term(self):
        """Map lookalikes only inside mixed-script words: dеlvе is an
        obfuscated Latin token, while ordinary Cyrillic prose is not."""
        data = slopscore.load_patterns()
        result = slopscore.score_text(
            "We should d\u0435lv\u0435 into the intricate tapestry before launch.", data
        )
        names = {hit["name"] for hit in result["hits"]}
        self.assertIn("delve", names)
        self.assertEqual(result["normalization"]["homoglyphs"], 2)
        cyrillic = slopscore.score_text("Мы обсудили релиз и исправили ошибку.", data)
        self.assertEqual(cyrillic["normalization"]["homoglyphs"], 0)
        self.assertFalse(any(hit["name"] == "normalization-bypass"
                             for hit in cyrillic["hits"]))

    def test_normalization_artifact_requires_a_cluster(self):
        data = slopscore.load_patterns()
        one = slopscore.score_text(
            "A plain note copied from an editor\u200b still reads like a plain note.", data
        )
        two = slopscore.score_text(
            "A note\u200b with two\u2060 invisible separators was pasted here.", data
        )
        self.assertFalse(any(hit["name"] == "normalization-bypass"
                             for hit in one["hits"]))
        self.assertTrue(any(hit["name"] == "normalization-bypass"
                            for hit in two["hits"]))

    def test_low_word_variety_is_a_corroborating_long_form_signal(self):
        """The incumbent's 1,654-paragraph corpus gave low TTR 22.46x lift,
        but one such signal must remain too weak to convict human prose."""
        data = slopscore.load_patterns()
        repetitive = ("The system runs the task and the system checks the task. " * 28)
        result = slopscore.score_text(repetitive, data)
        self.assertLess(result["type_token_ratio"], 0.4)
        self.assertTrue(any(hit["name"] == "low-word-variety"
                            for hit in result["hits"]))
        self.assertEqual(result["categories"]["rhythm"], 1.5)

    def test_low_word_variety_abstains_on_short_or_varied_text(self):
        data = slopscore.load_patterns()
        short = "The system repeats a word, but a short note cannot support this check."
        varied = (CORPUS / "personal-essay.txt").read_text()
        for text in (short, varied):
            with self.subTest(words=len(text.split())):
                result = slopscore.score_text(text, data)
                self.assertFalse(any(hit["name"] == "low-word-variety"
                                     for hit in result["hits"]))
        self.assertIsNone(slopscore.score_text(short, data)["type_token_ratio"])

    def test_code_fences_do_not_charge_cli_formatting(self):
        data = slopscore.load_patterns()
        plain = "A direct technical note about the release."
        fenced = plain + "\n\n```bash\ncommand --flag --another #tag 🚀\n```"
        a = slopscore.score_text(plain, data)
        b = slopscore.score_text(fenced, data)
        for field in ("emdash_per_100w", "emoji_count", "hashtags"):
            self.assertEqual(a[field], b[field], f"code changed {field}")

    def test_markdown_tables_do_not_charge_cli_formatting(self):
        data = slopscore.load_patterns()
        plain = "A direct technical note about the release."
        table = plain + (
            "\n\n| Method | Result |\n"
            "|---|---:|\n"
            "| **Overall** | **18/18** |"
        )
        a = slopscore.score_text(plain, data, formal=True)
        b = slopscore.score_text(table, data, formal=True)
        for field in ("emdash_per_100w", "bold_spans"):
            self.assertEqual(a[field], b[field], f"table changed {field}")

    def test_invalid_options_fail_cleanly(self):
        cases = [
            ["--gate"], ["--gate", "nan"], ["--gate", "101"],
            ["--genre"], ["--unknown"],
            ["--portfolio", "/path/that/does/not/exist/zero-slop"],
        ]
        for args in cases:
            with self.subTest(args=args):
                result = run([str(SCORER), *args])
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)

    def test_empty_batch_and_portfolio_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            for mode in ("--batch", "--portfolio"):
                with self.subTest(mode=mode):
                    result = run([str(SCORER), mode, td])
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("Traceback", result.stderr)

    def test_batch_json_is_structured_and_preserves_gate_exit_status(self):
        """Batch CI output must stay machine-readable; accepting --json and
        printing the human table makes the documented automation path unusable."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "clean.md").write_text(
                "The queue drained after the worker restarted. We checked the ledger."
            )
            (root / "slop.md").write_text(Detector.SLOP)
            result = run([str(SCORER), "--batch", td, "--json", "--gate", "25"])
            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["result_kind"], "batch_score")
            self.assertEqual(payload["documents"], 2)
            self.assertEqual(len(payload["items"]), 2)
            self.assertGreater(payload["max_score"], 25)
            self.assertTrue(payload["gate_applied"])
            self.assertFalse(payload["passed"])
            self.assertEqual(
                [row["score"] for row in payload["items"]],
                sorted((row["score"] for row in payload["items"]), reverse=True),
            )


class CommunityReportedSignals(unittest.TestCase):
    """Reader-reported research changes editorial priority without pretending
    that community frequency is a calibrated probability or a safe word list."""

    def test_runtime_names_the_reader_salience_pass_and_three_judgment_traits(self):
        skill = (ROOT / "SKILL.md").read_text().lower()
        tells = (ROOT / "references" / "tells.md").read_text().lower()
        readalong = (ROOT / "references" / "readalong.md").read_text().lower()
        evidence = (ROOT / "references" / "evidence.md").read_text().lower()

        self.assertIn("reader-salience pass", skill)
        for trait in (
            "reflexive agreement",
            "communicative drift",
            "rhetorical scale mismatch",
        ):
            with self.subTest(trait=trait):
                self.assertIn(trait, tells)
                self.assertIn(trait, readalong)
        self.assertIn("89,239", evidence)
        self.assertIn("jcarterjohnson/vibecoded-design-tells", evidence)
        self.assertIn("vocal, online", evidence)

    def test_judgment_fixture_pack_is_complete(self):
        root = DATA / "corpus" / "community-register" / "judgment"
        files = sorted(path.name for path in root.glob("*.txt"))
        self.assertEqual(files, [
            "communicative-drift.txt",
            "reflexive-agreement.txt",
            "rhetorical-scale-mismatch.txt",
        ])

    def test_generic_connectors_were_not_promoted_to_mechanical_tells(self):
        data = slopscore.load_patterns()
        lexicon = {term.lower() for term in data["lexicon"]}
        riders = {term.lower() for term in data.get("riders", {})}
        for term in ("however", "thus", "hence", "nuanced"):
            with self.subTest(term=term):
                self.assertNotIn(term, lexicon)
                self.assertNotIn(term, riders)

    def test_lingering_attention_frames_are_detected_without_banning_reasoned_return(self):
        data = slopscore.load_patterns()
        flagged = [
            "The line I keep coming back to is that agents need limits.",
            "I can't stop thinking about this launch note.",
            "That phrase has been rattling around in my head all week.",
            "I've been chewing on this since the meeting.",
        ]
        for text in flagged:
            with self.subTest(kind="flagged", text=text):
                hits = slopscore.score_text(text, data)["hits"]
                self.assertTrue(any(hit["name"] == "lingering-attention"
                                    for hit in hits))
        reasoned = ("I keep coming back to Hirschman's exit-voice framing because "
                    "it predicts which engineers quit and which ones file an RFC.")
        hits = slopscore.score_text(reasoned, data)["hits"]
        self.assertFalse(any(hit["name"] == "lingering-attention" for hit in hits))

    def test_social_endorsement_closers_need_a_curatorial_anchor(self):
        data = slopscore.load_patterns()
        flagged = [
            "This one is worth your time.",
            "Do yourself a favor and read this.",
            "You don't want to miss this!",
            "Don't sleep on this one.",
        ]
        for text in flagged:
            with self.subTest(kind="flagged", text=text):
                hits = slopscore.score_text(text, data)["hits"]
                self.assertTrue(any(hit["name"] == "social-endorsement-closer"
                                    for hit in hits))
        literal = [
            "She will thank me later when the deploy finishes.",
            "Read the runbook before you restart the worker.",
            "Don't miss this meeting; finance moved it to Thursday.",
        ]
        for text in literal:
            with self.subTest(kind="literal", text=text):
                hits = slopscore.score_text(text, data)["hits"]
                self.assertFalse(any(hit["name"] == "social-endorsement-closer"
                                     for hit in hits))

    def test_chat_roleplay_actions_are_artifacts_but_ordinary_italics_are_not(self):
        data = slopscore.load_patterns()
        flagged = "I understand the request. *nods thoughtfully* Here is the answer."
        clean = "Use *careful review* for this section and keep **bold text** intact."
        self.assertTrue(any(hit["name"] == "chat-roleplay-action"
                            for hit in slopscore.score_text(flagged, data)["hits"]))
        self.assertFalse(any(hit["name"] == "chat-roleplay-action"
                             for hit in slopscore.score_text(clean, data)["hits"]))

    def test_ai_tool_tracking_parameters_survive_url_masking(self):
        data = slopscore.load_patterns()
        trackers = (
            "utm_source=chatgpt.com", "utm_source=openai.com",
            "utm_source=copilot.com", "utm_source=claude.ai",
            "utm_source=perplexity.ai", "utm_source=gemini.google.com",
            "referrer=grok.com",
        )
        for tracker in trackers:
            with self.subTest(tracker=tracker):
                text = f"Read the source at https://example.com/report?{tracker}."
                hits = slopscore.score_text(text, data)["hits"]
                self.assertTrue(any(hit["name"] == "chatgpt-artifact" for hit in hits))

    def test_incumbent_phrase_signals_are_narrow_and_context_safe(self):
        """Adopt the incumbent's defensible phrase families without turning
        ordinary novelty, emotion, or direct answers into automatic verdicts."""
        data = slopscore.load_patterns()
        positives = {
            "reasoning-artifact": "Let me think step by step before I answer.",
            "novelty-inflation": "This is the failure mode nobody is naming.",
            "emotional-flatline": "What surprised me most was the final result.",
            "acknowledgment-loop": "To answer your question, the cache expires hourly.",
        }
        for expected, text in positives.items():
            with self.subTest(kind="positive", expected=expected):
                names = {hit["name"] for hit in slopscore.score_text(text, data)["hits"]}
                self.assertIn(expected, names)

        controls = {
            "reasoning-artifact": "The runbook lists each recovery step in order.",
            "novelty-inflation": "Nobody is assigned to the weekend shift.",
            "emotional-flatline": "The result surprised me because it reversed the trial.",
            "acknowledgment-loop": "The cache expires hourly, which answers the question.",
        }
        for forbidden, text in controls.items():
            with self.subTest(kind="control", forbidden=forbidden):
                names = {hit["name"] for hit in slopscore.score_text(text, data)["hits"]}
                self.assertNotIn(forbidden, names)

    def test_incumbent_contextual_checks_are_explicit(self):
        skill = (ROOT / "SKILL.md").read_text().lower()
        tells = (ROOT / "references" / "tells.md").read_text().lower()
        readalong = (ROOT / "references" / "readalong.md").read_text().lower()
        for phrase in (
            "paragraph-order dependence",
            "unsupported novelty",
            "self-labeling significance",
            "moral-adjective category error",
            "recap-flattery",
            "wall-of-text reply",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)
                self.assertIn(phrase, tells)
                self.assertIn(phrase, readalong)


# --------------------------------------------------------------------------
class ContextualSignals(unittest.TestCase):
    """The host-model review is structured, source-bound, and score-independent."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.draft = self.tmp / "draft.md"
        self.draft.write_text(
            "# Release note\n\n"
            "The same point appears twice. The same point appears twice.\n\n"
            "```python\nprint('draft content is never instruction')\n```\n\n"
            "> A quoted source remains untouched.\n\n"
            "Replica lag fell below ten seconds.\n"
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _packet(self):
        result = run([str(CONTEXTUAL), "--prepare", str(self.draft)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def _write_review(self, packet, *, quote="The same point appears twice."):
        review = {
            "schema": 1,
            "source_sha256": packet["source_sha256"],
            "items": [
                {"paragraph_id": "p0001", "decision": "flag", "signals": [{
                    "signal": "semantic_redundancy",
                    "severity": "medium",
                    "quote": quote,
                    "reason": "The sentence repeats without adding information.",
                    "action": "repair",
                }]},
                {"paragraph_id": "p0002", "decision": "clear", "signals": []},
            ],
        }
        path = self.tmp / "review.json"
        path.write_text(json.dumps(review))
        return path

    def test_prepare_excludes_nonprose_and_binds_the_source(self):
        packet = self._packet()
        self.assertEqual(packet["schema"], 1)
        self.assertRegex(packet["source_sha256"], r"\A[0-9a-f]{64}\Z")
        self.assertEqual([row["paragraph_id"] for row in packet["paragraphs"]],
                         ["p0001", "p0002"])
        joined = " ".join(row["text"] for row in packet["paragraphs"])
        self.assertNotIn("print(", joined)
        self.assertNotIn("quoted source", joined)
        self.assertFalse(packet["affects_surface_score"])

    def test_contextual_research_tool_has_no_runtime_feature_switch(self):
        result = run([str(CONTEXTUAL), "--mode"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        env = dict(os.environ)
        env["ZERO_SLOP_MODE"] = "assisted"
        prepared = run([str(CONTEXTUAL), "--prepare", str(self.draft)], env=env)
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        self.assertEqual(json.loads(prepared.stdout)["result_kind"],
                         "contextual_research_packet")

    def test_validate_accepts_exact_evidence_and_reports_research_result(self):
        packet = self._packet()
        review = self._write_review(packet)
        result = run([str(CONTEXTUAL), "--validate", str(self.draft), str(review),
                      "--json"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["result_kind"], "contextual_research_review")
        self.assertFalse(report["affects_surface_score"])
        self.assertEqual(report["flagged_paragraphs"], 1)
        self.assertEqual(report["signals"], {"semantic_redundancy": 1})

    def test_validate_rejects_invented_quote_and_stale_source(self):
        packet = self._packet()
        invented = self._write_review(packet, quote="Words that are not in the draft.")
        result = run([str(CONTEXTUAL), "--validate", str(self.draft), str(invented),
                      "--json"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

        packet = self._packet()
        review = self._write_review(packet)
        self.draft.write_text(self.draft.read_text() + "\nChanged after review.\n")
        stale = run([str(CONTEXTUAL), "--validate", str(self.draft), str(review),
                     "--json"])
        self.assertNotEqual(stale.returncode, 0)
        self.assertNotIn("Traceback", stale.stderr)

    def test_validate_rejects_unknown_labels_probabilities_and_partial_reviews(self):
        packet = self._packet()
        review = json.loads(self._write_review(packet).read_text())
        review["items"][0]["signals"][0]["signal"] = "sounds_bad"
        path = self.tmp / "bad-label.json"
        path.write_text(json.dumps(review))
        self.assertNotEqual(
            run([str(CONTEXTUAL), "--validate", str(self.draft), str(path),
                 "--json"]).returncode,
            0,
        )

        review = json.loads(self._write_review(packet).read_text())
        review["items"][0]["signals"][0]["probability"] = 0.99
        path.write_text(json.dumps(review))
        self.assertNotEqual(
            run([str(CONTEXTUAL), "--validate", str(self.draft), str(path),
                 "--json"]).returncode,
            0,
        )

        review = json.loads(self._write_review(packet).read_text())
        review["items"] = review["items"][:1]
        path.write_text(json.dumps(review))
        self.assertNotEqual(
            run([str(CONTEXTUAL), "--validate", str(self.draft), str(path),
                 "--json"]).returncode,
            0,
        )

    def test_prepare_is_linear_enough_for_large_documents(self):
        self.draft.write_text("\n\n".join(
            f"Paragraph {i} records one specific operational fact." for i in range(2000)
        ))
        started = time.perf_counter()
        packet = self._packet()
        self.assertLess(time.perf_counter() - started, 3.0)
        self.assertEqual(len(packet["paragraphs"]), 2000)

    def test_mismatched_fence_marker_cannot_leak_code_into_review(self):
        self.draft.write_text(
            "Opening prose.\n\n```text\ninside code\n~~~\nstill code\n```\n\nClosing prose.\n"
        )
        packet = self._packet()
        self.assertEqual([row["text"] for row in packet["paragraphs"]],
                         ["Opening prose.", "Closing prose."])


# --------------------------------------------------------------------------
class ReflectLoop(unittest.TestCase):
    """The learning path. Every test runs against a throwaway copy of data/."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(DATA, self.tmp / "data")
        self._save = (learn.DATA, learn.OBS, learn.CORPUS, learn.SHARED,
                      learn.SHARED_LOG, learn.LOCAL, learn.LOCAL_LOG)
        learn.DATA = self.tmp / "data"
        learn.CORPUS = learn.DATA / "corpus" / "must-not-flag"
        learn.SHARED = learn.DATA / "learned.json"
        learn.SHARED_LOG = learn.DATA / "learned-log.md"
        private = self.tmp / "private"
        learn.OBS = private / "reflections.json"
        learn.LOCAL = private / "learned.json"
        learn.LOCAL_LOG = private / "learned-log.md"

    def tearDown(self):
        (learn.DATA, learn.OBS, learn.CORPUS, learn.SHARED,
         learn.SHARED_LOG, learn.LOCAL, learn.LOCAL_LOG) = self._save
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _pair(self, produced, shipped, doc, reason="unspecified", genre="general"):
        a, b = self.tmp / "p.md", self.tmp / "s.md"
        # Distinct surrounding content makes these distinct edit pairs. The
        # learning loop deliberately ignores caller-supplied IDs for recurrence.
        prefix = f"memo {doc}. "
        a.write_text(prefix + produced)
        b.write_text(prefix + shipped)
        learn.reflect(str(a), str(b), doc, reason=reason, genre=genre)

    def _obs(self):
        return json.loads(learn.OBS.read_text())["observations"]

    def _learned(self):
        if not learn.LOCAL.exists():
            return []
        return json.loads(learn.LOCAL.read_text())["patterns"]

    def _overlay(self):
        if not learn.LOCAL.exists():
            return learn.empty_learned("local")
        return json.loads(learn.LOCAL.read_text())

    # -- recurrence ------------------------------------------------------
    def test_single_document_cannot_mint_a_pattern(self):
        """The poisoning guard: one writer's idiosyncratic cut is not a tell."""
        before = len(self._learned())
        self._pair("We shipped it. This puts wood behind the arrow on latency for us.",
                   "We shipped it. Latency dropped.", "doc1")
        learn.promote(True, "test", 2.5)
        self.assertEqual(len(self._learned()), before)

    def test_promotes_only_after_threshold_documents(self):
        txt = "We shipped it. This puts wood behind the arrow on latency for us."
        cut = "We shipped it. Latency dropped."
        for i in range(learn.PROMOTE_AT):
            self._pair(txt, cut, f"doc{i}")
        before = len(self._learned())
        learn.promote(True, "test", 2.5)
        minted = self._learned()[before:]
        # Names are digests now — the readable phrase is the author's prose and
        # must not enter a tracked file. Assert on behaviour: some minted
        # pattern matches the span that recurred.
        self.assertTrue(any(re.search(p["rx"], "this puts wood behind the arrow on latency", re.I)
                            for p in minted),
                        f"the recurring tell was not minted: {[p['name'] for p in minted]}")
        preferred = [p for p in self._overlay().get("fix_preferences", [])
                     if p.get("preferred_fix") == "latency dropped"]
        self.assertTrue(preferred, "recurring human replacement did not reach fix memory")
        self.assertGreaterEqual(preferred[0].get("seen_in_pairs", 0), learn.PROMOTE_AT)

    def test_existing_detector_tell_can_teach_the_fix_memory(self):
        for i in range(learn.PROMOTE_AT):
            self._pair("We're thrilled to announce the release.",
                       "The release is live.", f"known-{i}")
        learn.promote(True, "test", 2.5)
        prefs = self._overlay().get("fix_preferences", [])
        self.assertTrue(any(p.get("source_span") == "we're thrilled to announce"
                            and p.get("preferred_fix") == "the release is live"
                            for p in prefs), prefs)
        obs = json.loads(learn.OBS.read_text())
        self.assertNotIn("thrilled", obs.get("lexicon_candidates", {}))
        self.assertNotIn("announce", obs.get("lexicon_candidates", {}))
        self._pair("We're thrilled to announce the release.",
                   "The release is live.", "known-refresh")
        learn.promote(True, "test", 2.5)
        refreshed = next(p for p in self._overlay()["fix_preferences"]
                         if p["source_span"] == "we're thrilled to announce")
        self.assertEqual(refreshed["seen_in_pairs"], learn.PROMOTE_AT + 1)
        self.assertTrue(refreshed["active"])

    def test_reason_and_genre_survive_promotion(self):
        for i in range(learn.PROMOTE_AT):
            self._pair("We're thrilled to announce the release.",
                       "The release is live.", f"reason-{i}",
                       reason="canned_framing", genre="linkedin")
        learn.promote(True, "test", 2.5)
        pref = next(p for p in self._overlay()["fix_preferences"]
                    if p["source_span"] == "we're thrilled to announce")
        self.assertEqual(pref["reasons"], {"canned_framing": learn.PROMOTE_AT})
        self.assertEqual(pref["genres"], {"linkedin": learn.PROMOTE_AT})

    def test_invalid_reason_and_genre_fail_closed(self):
        a, b = self.tmp / "p.md", self.tmp / "s.md"
        a.write_text("We're thrilled to announce the release.")
        b.write_text("The release is live.")
        with self.assertRaises(SystemExit):
            learn.reflect(str(a), str(b), reason="invented-label")
        with self.assertRaises(SystemExit):
            learn.reflect(str(a), str(b), genre="private-board-channel")

    def test_per_edit_feedback_can_label_mixed_reasons(self):
        for i in range(learn.PROMOTE_AT):
            produced = (f"Memo {i}. We're thrilled to announce the release. "
                        "Metrics held. At the end of the day, uptime improved.")
            shipped = (f"Memo {i}. The release is live. Metrics held. "
                       "Uptime improved.")
            a, b = self.tmp / "p.md", self.tmp / "s.md"
            a.write_text(produced)
            b.write_text(shipped)
            feedback = {
                "schema": 1,
                "source_sha256": learn.text_sha256(produced),
                "target_sha256": learn.text_sha256(shipped),
                "edits": [
                    {"source_span": "We're thrilled to announce",
                     "reason": "canned_framing", "genre": "linkedin"},
                    {"source_span": "At the end of the day,",
                     "reason": "semantic_redundancy", "genre": "linkedin"},
                ],
            }
            feedback_path = self.tmp / f"feedback-{i}.json"
            feedback_path.write_text(json.dumps(feedback))
            learn.reflect(str(a), str(b), feedback=feedback_path)
        learn.promote(True, "test", 2.5)
        prefs = {p["source_span"]: p for p in self._overlay()["fix_preferences"]}
        self.assertEqual(prefs["we're thrilled to announce"]["reasons"],
                         {"canned_framing": learn.PROMOTE_AT})
        self.assertEqual(prefs["at the end of the day"]["reasons"],
                         {"semantic_redundancy": learn.PROMOTE_AT})

    def test_per_edit_feedback_rejects_hash_mismatch_and_unknown_span(self):
        a, b = self.tmp / "p.md", self.tmp / "s.md"
        a.write_text("We're thrilled to announce the release.")
        b.write_text("The release is live.")
        payload = {
            "schema": 1,
            "source_sha256": "0" * 64,
            "target_sha256": learn.text_sha256(b.read_text()),
            "edits": [{"source_span": "We're thrilled to announce",
                       "reason": "canned_framing", "genre": "linkedin"}],
        }
        feedback = self.tmp / "feedback.json"
        feedback.write_text(json.dumps(payload))
        with self.assertRaises(SystemExit):
            learn.reflect(str(a), str(b), feedback=feedback)
        payload["source_sha256"] = learn.text_sha256(a.read_text())
        payload["edits"][0]["source_span"] = "not present in the diff"
        feedback.write_text(json.dumps(payload))
        with self.assertRaises(SystemExit):
            learn.reflect(str(a), str(b), feedback=feedback)

    def test_retrieval_is_relevant_bounded_and_not_a_probability(self):
        overlay = learn.empty_learned("local")
        overlay["fix_preferences"] = [
            {"source_span": "we're thrilled to announce",
             "preferred_fix": "the release is live", "seen_in_pairs": 5,
             "reasons": {"canned_framing": 5}, "genres": {"linkedin": 5},
             "active": True},
            {"source_span": "at the end of the day",
             "preferred_fix": "ultimately", "seen_in_pairs": 4,
             "reasons": {"canned_framing": 4}, "genres": {"email": 4},
             "active": True},
            {"source_span": "moves the needle for teams",
             "preferred_fix": "cuts deploy time", "seen_in_pairs": 3,
             "reasons": {"vague_reference": 3}, "genres": {"linkedin": 3},
             "active": True},
        ]
        learn.write_json(learn.LOCAL, overlay, private=True)
        rows = learn.retrieve_preferences(
            "We're thrilled to announce what shipped today.",
            reason="canned_framing", genre="linkedin", limit=2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["when"], "we're thrilled to announce")
        self.assertIn("similarity", rows[0])
        self.assertNotIn("probability", rows[0])
        self.assertLessEqual(rows[0]["similarity"], 1.0)

    def test_retrieval_abstains_without_lexical_relevance(self):
        overlay = learn.empty_learned("local")
        overlay["fix_preferences"] = [{
            "source_span": "we're thrilled to announce",
            "preferred_fix": "the release is live", "seen_in_pairs": 5,
            "reasons": {"canned_framing": 5}, "genres": {"linkedin": 5},
            "active": True,
        }]
        learn.write_json(learn.LOCAL, overlay, private=True)
        self.assertEqual(
            learn.retrieve_preferences("Replica lag fell below ten seconds.",
                                       reason="canned_framing", genre="linkedin"),
            [],
        )

    def test_retrieval_scales_to_large_private_overlays(self):
        overlay = learn.empty_learned("local")
        overlay["fix_preferences"] = [
            {"source_span": f"stock framing phrase {i}",
             "preferred_fix": f"plain wording {i}", "seen_in_pairs": 3,
             "reasons": {"canned_framing": 3}, "genres": {"general": 3},
             "active": True}
            for i in range(5000)
        ]
        started = time.perf_counter()
        rows = learn.retrieve_preferences("stock framing phrase 4242 appears here",
                                          reason="canned_framing", genre="general",
                                          limit=5, learned=overlay)
        self.assertLess(time.perf_counter() - started, 1.0)
        self.assertLessEqual(len(rows), 5)
        self.assertEqual(rows[0]["when"], "stock framing phrase 4242")

    def test_retrieval_fails_closed_on_unbounded_overlay(self):
        overlay = learn.empty_learned("local")
        row = {"source_span": "stock framing phrase",
               "preferred_fix": "plain wording", "seen_in_pairs": 3,
               "active": True}
        overlay["fix_preferences"] = [row] * (learn.MAX_RETRIEVAL_PREFERENCES + 1)
        with self.assertRaises(SystemExit):
            learn.retrieve_preferences("stock framing phrase", learned=overlay)

    def test_stale_fix_preference_is_retired(self):
        old = str(date.today() - timedelta(days=30 * (learn.DECAY_MONTHS + 2)))
        overlay = learn.empty_learned("local")
        overlay["fix_preferences"] = [{
            "source_span": "we're thrilled to announce",
            "preferred_fix": "the release is live",
            "seen_in_pairs": 3,
            "last_confirmed": old,
            "active": True,
        }]
        learn.write_json(learn.LOCAL, overlay, private=True)
        learn.decay_local()
        self.assertFalse(self._overlay()["fix_preferences"][0]["active"])

    def test_local_decay_is_idempotent_until_reconfirmed(self):
        old = str(date.today() - timedelta(days=30 * (learn.DECAY_MONTHS + 2)))
        overlay = learn.empty_learned("local")
        overlay["patterns"] = [{
            "name": "stale", "cat": "test", "rx": r"\bstale phrase\b",
            "w": 4.0, "last_confirmed": old,
        }]
        learn.write_json(learn.LOCAL, overlay, private=True)
        learn.decay_local()
        once = self._overlay()["patterns"][0]["w"]
        learn.decay_local()
        twice = self._overlay()["patterns"][0]["w"]
        self.assertEqual((once, twice), (2.0, 2.0))

    def test_confirmation_clears_the_decay_marker(self):
        old = str(date.today() - timedelta(days=30 * (learn.DECAY_MONTHS + 2)))
        overlay = learn.empty_learned("local")
        overlay["patterns"] = [{
            "name": "stale", "cat": "test", "rx": r"\bstale phrase\b",
            "w": 2.0, "last_confirmed": old, "decayed": str(date.today()),
        }]
        learn.write_json(learn.LOCAL, overlay, private=True)
        sample = self.tmp / "confirm.md"
        sample.write_text("This stale phrase appeared again.")
        learn.confirm(sample)
        pattern = self._overlay()["patterns"][0]
        self.assertNotIn("decayed", pattern)
        self.assertEqual(pattern["last_confirmed"], str(date.today()))

    def test_same_document_counted_once(self):
        """Re-running reflect on one doc must not inflate its way to threshold."""
        txt = "We shipped it. This puts wood behind the arrow on latency for us."
        cut = "We shipped it. Latency dropped."
        for _ in range(5):
            self._pair(txt, cut, "same-doc")
        counts = [v["count"] for v in self._obs().values()]
        self.assertTrue(all(c == 1 for c in counts), counts)

    # -- content filter --------------------------------------------------
    def test_ignores_cuts_containing_figures(self):
        self._pair("We raised 40M dollars last quarter here.", "We raised money.", "d")
        self.assertEqual(self._obs(), {})

    def test_ignores_cuts_containing_proper_nouns(self):
        self._pair("The tool from Acme Corp shipped.", "The tool shipped.", "d")
        for k in self._obs():
            self.assertNotIn("acme", k)

    # -- safety gate -----------------------------------------------------
    def test_fp_gate_rejects_any_corpus_phrase_directly(self):
        """Unit check on the gate itself, independent of the reflect path."""
        for phrase, src in [("that all men are created equal", "gettysburg.txt"),
                            ("the replica lag dashboard", "sre-runbook.txt")]:
            with self.subTest(phrase):
                self.assertIsNotNone(learn.fp_gate(learn.to_regex(phrase)),
                                     f"gate failed to protect {src}")

    def test_fp_gate_fails_closed_without_its_corpus(self):
        old = learn.CORPUS
        learn.CORPUS = self.tmp / "missing-safety-corpus"
        try:
            self.assertIn("missing", learn.fp_gate(r"\bnew phrase\b"))
        finally:
            learn.CORPUS = old

    def test_lexicon_coverage_uses_word_boundaries(self):
        self.assertIsNone(learn.already_caught("partial result", [], ["art"]))
        self.assertEqual(learn.already_caught("artistic result", [], ["art"]),
                         "lexicon:art")

    def test_gate_rejects_pattern_matching_certified_human_writing(self):
        """The gate that matters. A span lifted verbatim from the certified
        human corpus must never become a pattern, however many writers cut it."""
        planted = "that all men are created equal"     # lowercase, so the
        self.assertIsNone(learn.is_content_specific(planted))  # content filter
        self.assertIn(planted, (learn.CORPUS / "gettysburg.txt").read_text())
        for i in range(learn.PROMOTE_AT + 2):
            self._pair(f"Memo {'x' * i}. We hold that all men are created equal here.",
                       f"Memo {'x' * i}. We hold that.", f"doc{i}")
        ready = [k for k, v in self._obs().items()
                 if v["count"] >= learn.PROMOTE_AT and "created equal" in k]
        self.assertTrue(ready, f"setup failed, observations: {list(self._obs())}")
        before = len(self._learned())
        learn.promote(True, "test", 2.5)
        minted = [p["name"] for p in self._learned()[before:]]
        self.assertFalse([p for p in self._learned()[before:]
                          if re.search(p["rx"], "that all men are created equal", re.I)],
                         f"safety gate let a Gettysburg phrase through: {minted}")

    def test_promoted_pattern_carries_provenance(self):
        txt = "We shipped it. This puts wood behind the arrow on latency for us."
        cut = "We shipped it. Latency dropped."
        for i in range(learn.PROMOTE_AT):
            self._pair(txt, cut, f"doc{i}")
        before = len(self._learned())
        learn.promote(True, "test", 2.5)
        new = self._learned()[before:]
        self.assertTrue(new)
        for p in new:
            self.assertTrue(p.get("first_seen"))
            self.assertTrue(p.get("last_confirmed"))
            self.assertEqual(p.get("source"), "reflect")
            self.assertGreaterEqual(p.get("seen_in_docs", 0), learn.PROMOTE_AT)
            re.compile(p["rx"])

    def test_no_user_prose_in_tracked_files(self):
        """learned.json is committed. The author's sentences must not be in it.

        An `example` field and a phrase-derived pattern name put the user's own
        prose into a tracked file while --export printed "no source text is
        included". Names are digests now and there is no example field.
        """
        shared_before = learn.SHARED.read_text()
        txt = "We shipped it. This puts wood behind the arrow on latency for us."
        cut = "We shipped it. Latency dropped."
        for i in range(learn.PROMOTE_AT):
            self._pair(txt, cut, f"doc{i}")
        learn.promote(True, "test", 2.5)
        self.assertEqual(learn.SHARED.read_text(), shared_before,
                         "private online learning changed the tracked taxonomy")
        self.assertTrue(learn.LOCAL.exists(), "live learning overlay was not written")

    def test_promotion_is_not_repeated(self):
        txt = "We shipped it. This puts wood behind the arrow on latency for us."
        cut = "We shipped it. Latency dropped."
        for i in range(learn.PROMOTE_AT):
            self._pair(txt, cut, f"doc{i}")
        learn.promote(True, "test", 2.5)
        n = len(self._learned())
        learn.promote(True, "test", 2.5)
        self.assertEqual(len(self._learned()), n, "double-minted the same span")

    def test_learned_pattern_does_not_break_the_human_corpus(self):
        """After learning, the whole safety corpus must still score clean."""
        txt = "We shipped it. This puts wood behind the arrow on latency for us."
        cut = "We shipped it. Latency dropped."
        for i in range(learn.PROMOTE_AT):
            self._pair(txt, cut, f"doc{i}")
        learn.promote(True, "test", 2.5)
        for p in self._learned():
            cre = re.compile(p["rx"], re.I)
            for f in learn.CORPUS.glob("*.txt"):
                self.assertIsNone(cre.search(f.read_text()),
                                  f"{p['name']} convicts {f.name}")

    # -- generalization --------------------------------------------------
    def test_generated_regex_tolerates_inflection(self):
        rx = learn.to_regex("moves the needle")
        self.assertTrue(re.search(rx, "it moves the needle today", re.I))
        self.assertTrue(re.search(rx, "it moved the needle today", re.I))

    def test_generated_regex_tolerates_insertion(self):
        rx = learn.to_regex("at the end of the day")
        self.assertTrue(re.search(rx, "at the end of the day", re.I))
        self.assertTrue(re.search(rx, "at the very end of the day", re.I))


# --------------------------------------------------------------------------
class Decay(unittest.TestCase):
    """A tell from two model generations ago should fade on its own."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(DATA, self.tmp / "data")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_stale_pattern_is_halved(self):
        import calibrate
        saved = calibrate.DATA
        calibrate.DATA = self.tmp / "data"
        try:
            p = calibrate.DATA / "learned.json"
            d = json.loads(p.read_text())
            old = str(date.today() - timedelta(days=30 * 25))
            d["patterns"][0]["last_confirmed"] = old
            w0 = d["patterns"][0]["w"]
            p.write_text(json.dumps(d, indent=1))
            calibrate.decay()
            after = json.loads(p.read_text())["patterns"][0]["w"]
            self.assertAlmostEqual(after, round(w0 / 2, 2))
        finally:
            calibrate.DATA = saved

    def test_fresh_pattern_is_untouched(self):
        import calibrate
        saved = calibrate.DATA
        calibrate.DATA = self.tmp / "data"
        try:
            p = calibrate.DATA / "learned.json"
            d = json.loads(p.read_text())
            d["patterns"][0]["last_confirmed"] = str(date.today())
            w0 = d["patterns"][0]["w"]
            p.write_text(json.dumps(d, indent=1))
            calibrate.decay()
            self.assertEqual(json.loads(p.read_text())["patterns"][0]["w"], w0)
        finally:
            calibrate.DATA = saved

    def test_shared_decay_is_idempotent(self):
        import calibrate
        saved = calibrate.DATA
        calibrate.DATA = self.tmp / "data"
        try:
            p = calibrate.DATA / "learned.json"
            d = json.loads(p.read_text())
            d["patterns"][0]["last_confirmed"] = str(
                date.today() - timedelta(days=30 * 25))
            d["patterns"][0].pop("decayed", None)
            p.write_text(json.dumps(d, indent=1))
            calibrate.decay()
            once = json.loads(p.read_text())["patterns"][0]["w"]
            calibrate.decay()
            twice = json.loads(p.read_text())["patterns"][0]["w"]
            self.assertEqual(once, twice)
        finally:
            calibrate.DATA = saved

    def test_malformed_shared_pattern_fails_closed(self):
        import calibrate
        saved = calibrate.DATA
        calibrate.DATA = self.tmp / "data"
        try:
            path = calibrate.DATA / "learned.json"
            data = json.loads(path.read_text())
            data["patterns"].append("not-a-pattern")
            path.write_text(json.dumps(data))
            with self.assertRaises(SystemExit):
                calibrate.decay()
        finally:
            calibrate.DATA = saved


class CalibrationInputs(unittest.TestCase):
    """Calibration must fail closed instead of learning from empty or malformed data."""

    def test_missing_and_empty_corpora_are_rejected(self):
        import calibrate
        tmp = Path(tempfile.mkdtemp())
        try:
            with self.assertRaises(ValueError):
                calibrate.read_corpus(tmp / "missing")
            empty = tmp / "empty"
            empty.mkdir()
            with self.assertRaises(ValueError):
                calibrate.read_corpus(empty)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mixed_json_ignores_non_text_values(self):
        import calibrate
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "corpus.json").write_text(json.dumps([
                {"draft": "Useful prose here."}, 7, None, True,
                {"draft": 99}, "Second useful sample.",
            ]))
            self.assertEqual(calibrate.read_corpus(tmp),
                             ["Useful prose here.", "Second useful sample."])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_invalid_json_is_not_scored_as_prose(self):
        import calibrate
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "broken.json").write_text("{not valid json}")
            with self.assertRaises(ValueError):
                calibrate.read_corpus(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_calibration_refuses_to_overwrite_detector_state(self):
        import calibrate
        tmp = Path(tempfile.mkdtemp())
        old_data = calibrate.DATA
        try:
            calibrate.DATA = tmp / "data"
            calibrate.DATA.mkdir()
            human, ai = tmp / "human", tmp / "ai"
            human.mkdir(); ai.mkdir()
            (human / "a.txt").write_text("A plain human sentence with enough words.")
            (ai / "a.txt").write_text("Seamless seamless seamless seamless seamless output.")
            with self.assertRaises(SystemExit):
                calibrate.main(["--human", str(human), "--ai", str(ai),
                                "--out", str(calibrate.DATA / "learned.json")])
        finally:
            calibrate.DATA = old_data
            shutil.rmtree(tmp, ignore_errors=True)


class OnlineLearningSafety(unittest.TestCase):
    """Live adaptation is private, atomic, path-safe, and process-safe."""

    def test_local_overlay_is_loaded_on_the_next_score(self):
        tmp = Path(tempfile.mkdtemp())
        old_home = slopscore.HOME
        try:
            slopscore.HOME = tmp
            (tmp / "learned.json").write_text(json.dumps({
                "patterns": [{"name": "local-test", "cat": "test",
                              "rx": r"\bwood behind the arrow\b", "w": 4.0}],
                "lexicon": {}, "riders": {}
            }))
            data = slopscore.load_patterns()
            hits = slopscore.score_text(
                "This puts wood behind the arrow today.", data)["hits"]
            self.assertTrue(any(h["name"] == "local-test" for h in hits))
        finally:
            slopscore.HOME = old_home
            shutil.rmtree(tmp, ignore_errors=True)

    def test_malformed_local_overlay_degrades_to_shared_rules(self):
        tmp = Path(tempfile.mkdtemp())
        old_home = slopscore.HOME
        try:
            slopscore.HOME = tmp
            (tmp / "learned.json").write_text(json.dumps({
                "patterns": [
                    {"w": "bad"},
                    {"name": "missing-category", "rx": "plain", "w": 2.0},
                ]
            }))
            result = slopscore.score_text("A plain sentence.", slopscore.load_patterns())
            self.assertIn("ai_likelihood", result)
        finally:
            slopscore.HOME = old_home
            shutil.rmtree(tmp, ignore_errors=True)

    def test_pathological_local_regex_is_ignored(self):
        tmp = Path(tempfile.mkdtemp())
        old_home = slopscore.HOME
        try:
            slopscore.HOME = tmp
            (tmp / "learned.json").write_text(json.dumps({
                "patterns": [{"name": "nested-quantifier", "cat": "test",
                              "rx": r"(a+)+$", "w": 4.0}],
                "lexicon": {}, "riders": {},
            }))
            names = {p["name"] for p in slopscore.load_patterns()["patterns"]}
            self.assertNotIn("nested-quantifier", names)
        finally:
            slopscore.HOME = old_home
            shutil.rmtree(tmp, ignore_errors=True)

    def test_voice_names_cannot_escape_the_private_directory(self):
        for name in ("../outside", "/tmp/outside", "a/b"):
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    slopscore.load_patterns(voice=name)
                with self.assertRaises(SystemExit):
                    learn.safe_voice_name(name)

    def test_export_containment_rejects_prefix_siblings(self):
        root = Path("/tmp/zero-slop")
        self.assertFalse(learn.is_within(Path("/tmp/zero-slop-escape/x"), root))
        self.assertTrue(learn.is_within(root / "x", root))

    def test_corrupt_reflection_store_is_not_silently_overwritten(self):
        tmp = Path(tempfile.mkdtemp())
        p = tmp / "reflections.json"
        p.write_text("not json")
        try:
            with self.assertRaises(SystemExit):
                learn.load(p, {"observations": {}})
            self.assertEqual(p.read_text(), "not json")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_invalid_reflection_schema_fails_closed(self):
        tmp = Path(tempfile.mkdtemp())
        old_obs = learn.OBS
        try:
            learn.OBS = tmp / "reflections.json"
            learn.OBS.write_text(json.dumps({"observations": []}))
            with self.assertRaises(SystemExit):
                learn.load_observations()
            self.assertEqual(json.loads(learn.OBS.read_text()), {"observations": []})
        finally:
            learn.OBS = old_obs
            shutil.rmtree(tmp, ignore_errors=True)

    def test_reflection_counts_must_equal_unique_evidence_documents(self):
        tmp = Path(tempfile.mkdtemp())
        old_obs = learn.OBS
        try:
            learn.OBS = tmp / "reflections.json"
            for docs, count in [(["same", "same"], 2), (["one"], 7)]:
                with self.subTest(docs=docs, count=count):
                    learn.OBS.write_text(json.dumps({
                        "observations": {"a recurring phrase": {
                            "count": count, "docs": docs, "examples": [],
                        }},
                        "false_positives": {}, "lexicon_candidates": {},
                        "fix_observations": {},
                    }))
                    with self.assertRaises(SystemExit):
                        learn.load_observations()
        finally:
            learn.OBS = old_obs
            shutil.rmtree(tmp, ignore_errors=True)

    def test_invalid_confirmation_counter_fails_closed(self):
        tmp = Path(tempfile.mkdtemp())
        overlay = tmp / "learned.json"
        overlay.write_text(json.dumps({
            "patterns": [{
                "name": "bad-counter", "cat": "test", "rx": "plain",
                "w": 2.0, "confirmations": "many",
            }],
            "lexicon": {}, "riders": {}, "fix_preferences": [],
        }))
        try:
            with self.assertRaises(SystemExit):
                learn.load_learned(overlay, "local")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_nested_fix_documents_must_be_strings(self):
        tmp = Path(tempfile.mkdtemp())
        old_obs = learn.OBS
        try:
            learn.OBS = tmp / "reflections.json"
            learn.OBS.write_text(json.dumps({
                "observations": {}, "false_positives": {},
                "lexicon_candidates": {},
                "fix_observations": {"tell": {
                    "count": 1, "docs": ["outer"],
                    "replacements": {"fix": {"count": 1, "docs": [7]}},
                }},
            }))
            with self.assertRaises(SystemExit):
                learn.load_observations()
        finally:
            learn.OBS = old_obs
            shutil.rmtree(tmp, ignore_errors=True)

    def test_false_positive_weights_and_applied_fix_counts_are_bounded(self):
        tmp = Path(tempfile.mkdtemp())
        old_obs = learn.OBS
        try:
            learn.OBS = tmp / "reflections.json"
            malformed = [
                {
                    "observations": {},
                    "false_positives": {"rule": {
                        "count": 1, "docs": ["doc"], "quotes": [], "weight": "high",
                    }},
                    "lexicon_candidates": {}, "fix_observations": {},
                },
                {
                    "observations": {}, "false_positives": {},
                    "lexicon_candidates": {},
                    "fix_observations": {"tell": {
                        "count": 1, "docs": ["doc"], "applied_count": 2,
                        "replacements": {"fix": {"count": 1, "docs": ["doc"]}},
                    }},
                },
            ]
            for payload in malformed:
                with self.subTest(payload=payload):
                    learn.OBS.write_text(json.dumps(payload))
                    with self.assertRaises(SystemExit):
                        learn.load_observations()
        finally:
            learn.OBS = old_obs
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_confirmation_and_voice_paths_fail_closed(self):
        with self.assertRaises(SystemExit):
            learn.confirm("/path/that/does/not/exist/zero-slop-confirm")
        with self.assertRaises(SystemExit):
            learn.build_voice("test", "/path/that/does/not/exist/zero-slop-voice")

    def test_missing_reflection_inputs_fail_without_traceback(self):
        result = run([
            str(LEARNER), "--reflect", "--produced",
            "/path/that/does/not/exist/produced.md", "--shipped",
            "/path/that/does/not/exist/shipped.md",
        ])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

    def test_nonfinite_weights_are_rejected_at_the_cli(self):
        for value in ("nan", "inf", "-1", "10.1"):
            with self.subTest(value):
                r = run([str(LEARNER), "--stats", "--weight", value])
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_malformed_contributions_fail_cleanly(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            not_object = tmp / "list.json"
            not_object.write_text("[]")
            self.assertEqual(learn.merge(str(not_object), False, "test", 2.5), 1)

            bad_count = tmp / "bad-count.json"
            bad_count.write_text(json.dumps({
                "schema": 1,
                "spans": [{"span": "wood behind the arrow", "documents": "many"}],
                "false_positives": [],
            }))
            self.assertEqual(learn.merge(str(bad_count), False, "test", 2.5), 0)

            duplicate = tmp / "duplicate.json"
            duplicate.write_text(json.dumps({
                "schema": 1,
                "spans": [
                    {"span": "wood behind the arrow", "documents": 3},
                    {"span": "Wood behind the arrow", "documents": 3},
                ],
                "false_positives": [],
            }))
            self.assertEqual(learn.merge(str(duplicate), False, "test", 2.5), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_concurrent_reflections_do_not_lose_updates(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            env = dict(os.environ, ZERO_SLOP_HOME=str(tmp / "state"))

            def one(i):
                produced = tmp / f"produced-{i}.md"
                shipped = tmp / f"shipped-{i}.md"
                produced.write_text(
                    f"memo {i}. We shipped it. This puts wood behind the arrow "
                    "on latency for us.")
                shipped.write_text(f"memo {i}. We shipped it. Latency dropped.")
                return subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "learn.py"),
                     "--reflect", "--produced", str(produced), "--shipped",
                     str(shipped), "--doc-id", f"doc-{i}"],
                    cwd=ROOT, env=env, capture_output=True, text=True)

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(one, range(8)))
            self.assertTrue(all(r.returncode == 0 for r in results),
                            "\n".join(r.stderr for r in results))
            state = json.loads((tmp / "state" / "reflections.json").read_text())
            counts = [v["count"] for v in state["observations"].values()]
            self.assertIn(8, counts, counts)
            if os.name != "nt":
                mode = (tmp / "state" / "reflections.json").stat().st_mode & 0o777
                self.assertEqual(mode, 0o600)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

# --------------------------------------------------------------------------
class Scale(unittest.TestCase):
    """Throughput and robustness at volumes a team would actually hit."""

    def test_throughput_on_a_thousand_documents(self):
        data = slopscore.load_patterns()
        doc = (CORPUS / "technical-postmortem.txt").read_text()
        t0 = time.perf_counter()
        for _ in range(1000):
            slopscore.score_text(doc, data)
        dt = time.perf_counter() - t0
        print(f"\n    1000 docs in {dt:.2f}s = {1000/dt:.0f} docs/sec "
              f"({dt/1000*1000:.2f} ms/doc)")
        self.assertLess(dt, 60, "scoring is too slow to gate CI")

    def test_large_document_does_not_blow_up(self):
        data = slopscore.load_patterns()
        big = (CORPUS / "personal-essay.txt").read_text() * 200
        t0 = time.perf_counter()
        r = slopscore.score_text(big, data)
        dt = time.perf_counter() - t0
        print(f"    {len(big.split()):,}-word document in {dt:.2f}s")
        self.assertLess(dt, 30)
        self.assertTrue(0 <= r["ai_likelihood"] <= 100)

    def test_pathological_input_terminates(self):
        """Guards against catastrophic backtracking in any shipped regex."""
        data = slopscore.load_patterns()
        for evil in ["a" * 60000, ("the " * 12000), ("— " * 6000), "\n" * 30000]:
            t0 = time.perf_counter()
            slopscore.score_text(evil, data)
            self.assertLess(time.perf_counter() - t0, 15,
                            f"backtracking on {evil[:12]!r}")

    def test_score_is_bounded_on_extremes(self):
        data = slopscore.load_patterns()
        worst = Detector.SLOP * 50
        s = slopscore.score_text(worst, data)["ai_likelihood"]
        self.assertLessEqual(s, 100)
        self.assertGreaterEqual(s, 0)

    def test_reflect_scales_to_a_large_diff(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            a, b = tmp / "a.md", tmp / "b.md"
            a.write_text("This puts wood behind the arrow on latency. " * 800)
            b.write_text("Latency dropped. " * 800)
            saved = (learn.OBS,)
            learn.OBS = tmp / "obs.json"
            t0 = time.perf_counter()
            learn.reflect(str(a), str(b), "big")
            dt = time.perf_counter() - t0
            print(f"    reflect on a 4,800-word diff in {dt:.2f}s")
            self.assertLess(dt, 30)
            learn.OBS = saved[0]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class DocsMatchReality(unittest.TestCase):
    """Numbers in the docs must equal numbers in the data.

    Every count in README.md, SKILL.md and the diagram is a factual claim about
    this repository, and they drift silently: the lexicon was described as
    72 terms for weeks after riders were split out and duplicate prefixes
    removed, leaving the real figure at 54. A skill whose whole premise is that
    unverified specifics are worse than vagueness cannot ship stale numbers
    about itself.
    """

    @classmethod
    def setUpClass(cls):
        b = json.loads((DATA / "patterns.json").read_text())
        l = json.loads((DATA / "learned.json").read_text())
        cls.n_pat = len(b["patterns"]) + len(l.get("patterns", []))
        cls.n_lex = len(b.get("lexicon", {})) + len(l.get("lexicon", {}))
        cls.n_rid = len(b.get("riders", {}))
        cls.n_corpus = len(list((DATA / "corpus" / "must-not-flag").glob("*.txt")))
        cls.docs = {f: (ROOT / f).read_text()
                    for f in ("README.md", "SKILL.md", "ONE-PAGER.md",
                              "assets/engine.svg")}

    def _claims(self, text, unit):
        """Every '<number> <unit>' assertion in a document."""
        return {int(m) for m in re.findall(rf"(\d+)[- ]?{unit}", text, re.I)}

    def test_pattern_count_is_accurate(self):
        """Claims about the regex database. Distinct from the tells.md catalogue:
        one tell can need several regexes, so the two numbers legitimately
        differ and the docs must not blur them."""
        for name, text in self.docs.items():
            # the "(N tells, M families)" form is the tells.md catalogue, checked
            # separately below; remove it so it is not read as a regex-count claim
            body = re.sub(r"\(\d+ tells, \d+ families\)", "", text)
            for claimed in self._claims(body, r"(?:weighted )?(?:tells|patterns|regexes)"):
                with self.subTest(f"{name}: {claimed}"):
                    self.assertEqual(claimed, self.n_pat,
                                     f"{name} claims {claimed} patterns, data has {self.n_pat}")

    def test_taxonomy_count_is_accurate(self):
        """The 'N tells, 6 families' claim must match references/tells.md."""
        src = (ROOT / "references" / "tells.md").read_text()
        fam, counts = None, {}
        for ln in src.split("\n"):
            m = re.match(r"^## (.+)", ln)
            if m:
                fam = m.group(1); counts.setdefault(fam, 0); continue
            if fam and ln.startswith("|") and not re.match(r"^\|[\s:|-]+\|?\s*$", ln):
                head = [c.strip().lower() for c in ln.strip("|").split("|")]
                if head and head[0] in ("tell", "pattern", "what", "construction", "signal"):
                    continue
                counts[fam] += 1
        families = [k for k in counts if not k.startswith("What is NOT")]
        n_tells = sum(counts[k] for k in families)
        for name, text in self.docs.items():
            for claimed, fams in re.findall(r"\((\d+) tells, (\d+) families\)", text):
                with self.subTest(f"{name}"):
                    self.assertEqual(int(claimed), n_tells,
                                     f"{name} claims {claimed} tells, tells.md has {n_tells}")
                    self.assertEqual(int(fams), len(families),
                                     f"{name} claims {fams} families, tells.md has {len(families)}")

    def test_lexicon_count_is_accurate(self):
        for name, text in self.docs.items():
            for claimed in self._claims(text, r"term lexicon"):
                with self.subTest(f"{name}: {claimed}"):
                    self.assertEqual(claimed, self.n_lex,
                                     f"{name} claims a {claimed}-term lexicon, data has {self.n_lex}")

    def test_rider_count_is_accurate(self):
        for name, text in self.docs.items():
            for claimed in self._claims(text, r"(?:context-gated )?riders"):
                with self.subTest(f"{name}: {claimed}"):
                    self.assertEqual(claimed, self.n_rid,
                                     f"{name} claims {claimed} riders, data has {self.n_rid}")

    def test_calibration_anchors_match_the_corpora(self):
        """The README teaches the scale with two numbers. Both must be measured.

        Counts were not the only thing that drifted: the README told readers raw
        AI drafts average 76 and human writing lands 9-29, when the benchmark
        corpus averages 70 and the human corpus spans 10-20. A scale explained
        with wrong anchors misleads every reader who then interprets a score.
        """
        import statistics as _st
        data = slopscore.load_patterns()
        drafts = [slopscore.score_text(e["draft"], data)["ai_likelihood"]
                  for e in json.loads((ROOT / "bench" / "examples.json").read_text())]
        human = [slopscore.score_text(f.read_text(), data)["ai_likelihood"]
                 for f in CORPUS.glob("*.txt")]
        ai_mean, lo, hi = _st.mean(drafts), min(human), max(human)
        normalized = re.sub(r"\s+", " ", self.docs["README.md"])
        m = re.search(
            r"(?:raw|unedited) AI drafts[^.]{0,45}?\b(?:average|averaged|mean)"
            r"\D{0,10}(\d{2})\b",
            normalized,
            re.IGNORECASE,
        )
        self.assertIsNotNone(m, "README no longer states the AI-draft anchor")
        self.assertAlmostEqual(int(m.group(1)), ai_mean, delta=2,
                               msg=f"README says drafts average {m.group(1)}, measured {ai_mean:.1f}")
        m2 = re.search(
            r"human (?:writing|samples)[^.]{0,45}?"
            r"(?:lands? between|scored(?: from)?) (\d+) (?:and|to) (\d+)",
            normalized,
            re.IGNORECASE,
        )
        self.assertIsNotNone(m2, "README no longer states the human-writing anchor")
        c_lo, c_hi = int(m2.group(1)), int(m2.group(2))
        self.assertLessEqual(c_lo, lo, f"README floor {c_lo} above measured {lo:.1f}")
        self.assertGreaterEqual(c_hi, hi, f"README ceiling {c_hi} below measured {hi:.1f}")
        self.assertLess(c_hi - hi, 8, f"README ceiling {c_hi} overstates measured max {hi:.1f}")

    def test_readme_is_compact_and_uses_current_results(self):
        readme = self.docs["README.md"]
        words = len(readme.split())
        self.assertGreaterEqual(words, 1000, "README lost essential operating detail")
        self.assertLessEqual(words, 1250, "README exceeded the two-page editorial brief")
        self.assertIn("RAID+", readme)
        self.assertIn("7,627", readme)
        compact = re.sub(r"\s+", " ", readme)
        self.assertIn("matched the prior 84.2% result", compact)
        self.assertIn("not independent human field accuracy", compact)
        speed = json.loads((ROOT / "bench" / "version-comparison.json").read_text())[
            "timing_seconds"
        ]["median_speed_change_pct"]
        if speed >= 0:
            timing_claim = f"{speed:.2f}% higher median throughput"
        else:
            timing_claim = f"{abs(speed):.2f}% lower"
        self.assertIn(timing_claim, compact)
        self.assertNotIn("Two independent LLMs", readme)
        self.assertNotIn("55/40", readme)
        self.assertNotIn("blind judges", readme.lower())

    def test_readme_uses_reader_language(self):
        readme = self.docs["README.md"].lower()
        # Link destinations may keep stable filenames; rendered prose may not
        # expose the scoring code's internal vocabulary.
        rendered = re.sub(r"\]\([^)]*\)", "]", readme)
        for term in (
                "surface score", "surface scorer", "weighted tells",
                "tell density", "burstiness", "followability", "scorecard",
                "heatmap", "fidelity gate", "private overlay",
                "evidence behind the score"):
            with self.subTest(term=term):
                self.assertNotIn(term, rendered)
        self.assertIn("writing score", rendered)
        self.assertIn("flagged phrases", rendered)

    def test_readme_explains_which_ai_does_the_editing(self):
        readme = " ".join(self.docs["README.md"].lower().split())
        self.assertIn("not an ai model", readme)
        self.assertIn("your ai assistant", readme)
        self.assertIn("claude, gpt, or another compatible model", readme)
        self.assertIn("local tools", readme)

    def test_readme_explains_the_eight_role_pipeline_honestly(self):
        readme = " ".join(self.docs["README.md"].lower().split())
        roles = (
            "1. scorer", "2. interpreter", "3. rewriter", "4. fact gate",
            "5. copy desk", "6. read-aloud editor", "7. verifier",
            "8. fresh-eyes finalizer",
        )
        self.assertIn("eight roles form one workflow", readme)
        self.assertIn("jobs, not separate models", readme)
        self.assertIn("research supports the checks, not the number eight", readme)
        positions = [readme.index(role) for role in roles]
        self.assertEqual(positions, sorted(positions), "README role order drifted")
        self.assertIn("any final polish restarts the final checks", readme)

    def test_skill_enforces_the_same_eight_role_pipeline(self):
        skill = " ".join(self.docs["SKILL.md"].lower().split())
        contract = skill[skill.index("## eight roles, one pipeline"):
                         skill.index("## detailed workflow")]
        roles = (
            "1. **scorer", "2. **interpreter", "3. **rewriter",
            "4. **fact gate", "5. **copy desk", "6. **read-aloud editor",
            "7. **verifier", "8. **fresh-eyes finalizer",
        )
        positions = [contract.index(role) for role in roles]
        self.assertEqual(positions, sorted(positions), "skill role order drifted")
        self.assertIn("separate jobs, not eight models or services", contract)
        self.assertIn("local tools plus the ai assistant", contract)
        self.assertIn("any repair returns through roles 5 and 6", contract)
        self.assertIn("a role 8 edit restarts roles 5 through 8", contract)

    def test_fresh_eyes_finalizer_is_separate_and_closed_loop(self):
        skill = self.docs["SKILL.md"].lower()
        brief = (ROOT / "references" / "fresh-eyes.md").read_text().lower()
        self.assertIn("### 8. fresh-eyes finalizer", skill)
        readaloud = skill[skill.index("### 6. read-aloud editor"):
                          skill.index("### 7. verifier")]
        self.assertIn("dedicated read-aloud editor", readaloud)
        self.assertNotIn("dedicated fresh-eyes editor", readaloud)
        for phrase in (
            "first-time reader", "approve without changes", "copy desk",
            "read-aloud", "verifier", "three rounds", "same exact text",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, brief)
        self.assertIn("references/fresh-eyes.md", skill)

    def test_skill_report_template_speaks_to_the_writer(self):
        skill = self.docs["SKILL.md"]
        summary = re.search(
            r"\*\*\(b\) The before-and-after summary\.\*\*.*?```(.*?)```",
            skill,
            re.S,
        )
        self.assertIsNotNone(summary, "plain-language report template is missing")
        template = summary.group(1).lower()
        for phrase in (
                "writing score", "flagged phrases", "sentence variety",
                "readability", "facts remain", "nothing new was added"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, template)
        for term in (
                "surface score", "weighted tells", "tell density", "burstiness",
                "followability", "fidelity", "scorecard", "heatmap", "artifact",
                "candidate", "overlay"):
            with self.subTest(term=term):
                self.assertNotIn(term, template)
        report = skill[skill.index("### 9. Report in plain language"):]
        self.assertIn("Who did what", report)
        self.assertIn("Your AI assistant", report)
        self.assertIn("never guess", report)

    def test_documented_cli_flags_exist(self):
        """A flag named in the README must be a flag the script accepts."""
        for script in ("slopscore.py", "learn.py", "calibrate.py"):
            src = (ROOT / "scripts" / script).read_text()
            for flag in re.findall(rf"scripts/{script} ([-\w ]*)", self.docs["README.md"]):
                for f in re.findall(r"--[a-z-]+", flag):
                    with self.subTest(f"{script} {f}"):
                        self.assertIn(f, src, f"README documents {f} but {script} has no such flag")

    def test_no_stale_version_references(self):
        import json as _j
        claude = _j.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        codex = _j.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())
        v = claude["version"]
        self.assertEqual(v, codex["version"], "plugin manifests disagree on version")
        self.assertIn(f'version: "{v}"', self.docs["SKILL.md"],
                      "SKILL.md version does not match the plugin manifest")
        self.assertIn(f"version-{v}", self.docs["README.md"],
                      "README badge does not match the plugin manifest")
        self.assertIn(f"v{v}", self.docs["ONE-PAGER.md"],
                      "one-pager does not match the plugin manifest")

    def test_skill_frontmatter_uses_supported_keys(self):
        header = self.docs["SKILL.md"].split("---", 2)[1]
        top = {m.group(1) for line in header.splitlines()
               if (m := re.match(r"^([a-z][a-z-]*):", line))}
        self.assertLessEqual(top, {"name", "description", "license", "metadata",
                                   "allowed-tools"})

    def test_plugin_manifests_have_required_identity(self):
        for folder in (".claude-plugin", ".codex-plugin"):
            manifest = json.loads((ROOT / folder / "plugin.json").read_text())
            with self.subTest(folder):
                for field in ("name", "version", "description", "author", "license"):
                    self.assertTrue(manifest.get(field), f"{folder} missing {field}")
                self.assertEqual(manifest["name"], "zero-slop")

    def test_removed_optimizer_is_absent(self):
        """The retired instruction optimizer must not survive in any runtime,
        generated bundle, document, benchmark, or filename."""
        banned = "skill" + "opt"
        roots = [ROOT / p for p in (
            "README.md", "SKILL.md", "ONE-PAGER.md", "SECURITY.md", "AGENTS.md",
            "references", "scripts", "data", "bench", "skills", "dist", "assets")]
        hits = []
        for root in roots:
            paths = [root] if root.is_file() else root.rglob("*") if root.exists() else []
            for path in paths:
                if banned in path.as_posix().lower():
                    hits.append(str(path.relative_to(ROOT)))
                    continue
                if path.is_file() and path.suffix.lower() in {
                        ".md", ".py", ".json", ".jsonl", ".yaml", ".yml", ".svg", ".txt"}:
                    if banned in path.read_text(errors="ignore").lower():
                        hits.append(str(path.relative_to(ROOT)))
        self.assertEqual(hits, [], f"retired optimizer still ships: {hits}")


class Discrimination(unittest.TestCase):
    """The meter must agree with an obvious human judgment, both directions."""

    def test_separates_known_slop_from_known_human(self):
        r = run([str(ROOT / "bench" / "discrimination" / "evaluate.py")])
        self.assertEqual(r.returncode, 0, r.stdout)


class SearchCorpus(unittest.TestCase):
    """Anonymous cross-genre examples stay reproducible and identifying-free."""

    PATH = ROOT / "bench" / "search-corpus" / "corpus.json"

    def test_scores_are_current_and_obvious_slop_is_caught(self):
        r = run([str(ROOT / "bench" / "search-corpus" / "evaluate.py"), "--check"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_same_corpus_comparison_is_current(self):
        r = run([str(ROOT / "bench" / "search-corpus" / "compare.py"), "--check"])
        self.assertEqual(r.returncode, 0, r.stdout)
        results = json.loads((self.PATH.parent / "comparison-results.json").read_text())
        self.assertEqual(set(results["methods"]),
                         {"zero-slop", "no-ai-slop", "humanizer", "de-slop",
                          "stop-slop"})
        for method, row in results["methods"].items():
            with self.subTest(method):
                self.assertEqual(row["automated_fact_check_passes"], 18)
                self.assertEqual(row["shape_gate_passes"], 18)
        self.assertEqual(results["methods"]["zero-slop"]["combined_passes"], 18)

    def test_comparison_outputs_cover_the_same_anonymous_ids(self):
        expected = {row["id"] for row in json.loads(self.PATH.read_text())}
        for path in sorted((self.PATH.parent / "outputs").glob("*.json")):
            with self.subTest(path.name):
                outputs = json.loads(path.read_text())
                self.assertEqual(set(outputs), expected)
                for text in outputs.values():
                    self.assertFalse(re.search(r"https?://|www\.|@[A-Za-z0-9_]", text))

    def test_corpus_is_anonymous_and_covers_every_platform_module(self):
        rows = json.loads(self.PATH.read_text())
        self.assertEqual(len(rows), 18)
        self.assertEqual({row["genre"] for row in rows},
                         {"linkedin", "x", "email", "blog", "newsletter", "research"})
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        for row in rows:
            with self.subTest(row["id"]):
                self.assertEqual(row["source_kind"], "anonymous_search_paraphrase")
                self.assertEqual(row["label"], "slop")
                self.assertFalse(re.search(r"https?://|www\.|@[A-Za-z0-9_]", row["text"]))
                self.assertFalse({"author", "username", "handle", "source_url"} & row.keys())

    def test_benchmark_scripts_are_portable(self):
        for path in (ROOT / "bench").rglob("*.py"):
            with self.subTest(path.relative_to(ROOT)):
                source = path.read_text()
                self.assertNotIn("/Users/", source)
                self.assertNotIn("\\\\Users\\\\", source)
                self.assertNotIn("/private/tmp/", source)

    def test_readme_table_matches_the_fresh_comparison_results(self):
        """The compact published replay must come from the JSON, not memory.

        External checker detail lives in bench/ rather than being duplicated in
        the executive README.
        """
        results = json.loads(
            (ROOT / "bench" / "fresh-replay" / "results.json").read_text()
        )
        readme = (ROOT / "README.md").read_text().replace("−", "-").replace("**", "")
        self.assertIn(
            f"| Original drafts | {results['originals']['mean_writing_score']:.1f} | "
            f"{results['originals']['zero_slop_release_passes']}/"
            f"{results['corpus']['drafts']} | — | — |",
            readme,
        )
        for row in results["methods"].values():
            expected = (
                f"| {row['label']} | {row['mean_writing_score']:.1f} | "
                f"{row['zero_slop_release_passes']}/{results['corpus']['drafts']} | "
                f"{row['zero_slop_fidelity_passes']}/{results['corpus']['drafts']} | "
                f"{row['mean_word_change_pct']:.1f}% |"
            )
            with self.subTest(method=row["label"]):
                self.assertIn(expected, readme)

        self.assertIn("[`bench/README.md`](bench/README.md)", readme)

    def test_fresh_replay_is_pinned_and_comparable(self):
        import hashlib

        root = ROOT / "bench" / "fresh-replay"
        result = json.loads((root / "results.json").read_text())
        self.assertEqual(result["result_kind"], "fresh_same_model_rewrite_replay")
        self.assertFalse(result["calibrated_field_accuracy"])
        self.assertEqual(result["corpus"]["drafts"], 18)
        self.assertEqual(result["corpus"]["genres"], 6)
        self.assertEqual(
            set(result["methods"]),
            {"zero-slop", "avoid-ai-writing", "no-ai-slop", "humanizer"},
        )
        settings = ("model", "reasoning_effort", "batch_size", "codex_cli",
                    "corpus_sha256")
        runs = []
        for method in result["methods"]:
            run_record = json.loads((root / "runs" / f"{method}.json").read_text())
            output = root / "outputs" / f"{method}.json"
            self.assertEqual(
                run_record["output_sha256"],
                hashlib.sha256(output.read_bytes()).hexdigest(),
            )
            runs.append(run_record)
        for field in settings:
            self.assertEqual(len({row[field] for row in runs}), 1, field)
        ours = result["methods"]["zero-slop"]
        self.assertEqual(ours["zero_slop_release_passes"], 18)
        self.assertEqual(ours["zero_slop_fidelity_passes"], 18)

    def test_incumbent_replay_is_method_hidden_and_reproducible(self):
        import hashlib

        root = ROOT / "bench" / "incumbent-blind-replay"
        result = json.loads((root / "results.json").read_text())
        self.assertEqual(
            result["result_kind"],
            "fresh_method_hidden_incumbent_rewrite_comparison",
        )
        self.assertFalse(result["calibrated_field_accuracy"])
        self.assertTrue(result["editorial_review"]["method_hidden"])
        self.assertEqual(result["corpus"]["drafts"], 18)
        self.assertEqual(result["corpus"]["genres"], 6)
        self.assertEqual(set(result["methods"]), {"zero-slop", "avoid-ai-writing"})
        self.assertEqual(result["methods"]["avoid-ai-writing"]["revision"],
                         "40328bd292bc682d46010a6f9ac2cdbf4fb4ceca")
        self.assertEqual(result["editorial_review"]["consensus"], {
            "zero-slop": 13, "avoid-ai-writing": 3, "tie": 0, "unresolved": 2,
        })
        self.assertEqual(
            result["editorial_review"]["exact_winner_agreement"]["items"], 16
        )
        self.assertEqual(
            result["deterministic_checks"]["zero-slop"]["zero_slop_fidelity_passes"],
            18,
        )
        self.assertEqual(
            result["deterministic_checks"]["avoid-ai-writing"]
                  ["zero_slop_fidelity_passes"],
            16,
        )

        runs = []
        for method in ("zero-slop", "avoid-ai-writing"):
            run = json.loads((root / "runs" / f"{method}.json").read_text())
            output = root / "outputs" / f"{method}.json"
            self.assertEqual(run["output_sha256"],
                             hashlib.sha256(output.read_bytes()).hexdigest())
            runs.append(run)
        for field in ("model", "reasoning_effort", "batch_size", "codex_cli",
                      "corpus_sha256"):
            self.assertEqual(len({run[field] for run in runs}), 1, field)

        self.assertEqual(len(result["editorial_review"]["passes"]), 2)
        for number in (1, 2):
            packet = root / "packets" / f"pass-{number}.json"
            packet_text = packet.read_text().lower()
            self.assertNotIn("zero-slop", packet_text)
            self.assertNotIn("avoid-ai-writing", packet_text)
        judge_source = (root / "judge.py").read_text()
        self.assertIn('"-C", str(temporary)', judge_source)
        self.assertIn('"--skip-git-repo-check"', judge_source)
        self.assertIn("not independent human field accuracy", result["limits"])

    def test_incumbent_transfer_audit_is_pinned_and_caveated(self):
        result = json.loads(
            (ROOT / "bench" / "incumbent-audit" / "results.json").read_text()
        )
        self.assertEqual(
            result["result_kind"], "pinned_incumbent_meter_transfer_audit"
        )
        self.assertFalse(result["calibrated_field_accuracy"])
        self.assertEqual(
            result["incumbent"]["commit"],
            "40328bd292bc682d46010a6f9ac2cdbf4fb4ceca",
        )
        self.assertEqual(result["panel"]["eligible_consensus_items"], 38)
        self.assertEqual(result["panel"]["held_out_test_items"], 21)
        self.assertIn("not human field accuracy", result["limits"])

    def test_readme_performance_table_matches_the_structured_record(self):
        result = json.loads((ROOT / "bench" / "performance-results.json").read_text())
        readme = re.sub(r"\s+", " ", (ROOT / "README.md").read_text())
        scorer = result["scorer"]
        self.assertIn(f"{scorer['median_batch_seconds']:.4f} seconds", readme)
        self.assertIn(f"{scorer['median_documents_per_second']:.1f} per second", readme)
        self.assertIn(f"{scorer['median_large_document_seconds']:.4f} seconds", readme)
        self.assertIn(
            f"{max(scorer['pathological_input_seconds'].values()):.4f} seconds",
            readme,
        )
        self.assertIn(
            f"{result['learning']['reflect_seconds']:.4f} seconds",
            readme,
        )

    def test_version_comparison_record_is_current_and_arithmetically_sound(self):
        import hashlib
        import statistics
        record = json.loads((ROOT / "bench" / "version-comparison.json").read_text())
        self.assertEqual(record["result_kind"], "interleaved_local_version_comparison")
        version = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())["version"]
        self.assertEqual(record["candidate"]["version"], version)
        self.assertEqual(
            record["candidate"]["slopscore_sha256"],
            hashlib.sha256(SCORER.read_bytes()).hexdigest(),
        )
        timing = record["timing_seconds"]
        old = statistics.median(timing["baseline"])
        new = statistics.median(timing["candidate"])
        self.assertAlmostEqual(timing["median_baseline"], old, places=4)
        self.assertAlmostEqual(timing["median_candidate"], new, places=4)
        self.assertAlmostEqual(timing["median_speed_change_pct"],
                               round((old / new - 1) * 100, 2), places=2)
        # Wall-clock medians move with scheduler noise. Treat a greater-than-5%
        # slowdown as a regression; publish the measured direction verbatim.
        self.assertGreater(timing["median_speed_change_pct"], -5.0)
        documents = record["workload"]["documents_per_run"]
        self.assertAlmostEqual(timing["documents_per_second_baseline"],
                               round(documents / old, 1), places=1)
        self.assertAlmostEqual(timing["documents_per_second_candidate"],
                               round(documents / new, 1), places=1)
        frozen = record["frozen_regression"]
        self.assertEqual(frozen["score_changes"], 0)
        self.assertEqual(frozen["known_human_below_gate_candidate"],
                         frozen["known_human_documents"])
        self.assertEqual(frozen["search_slop_caught_candidate"],
                         frozen["search_documents"])
        self.assertEqual(frozen["quality_candidate"], frozen["quality_baseline"])
        self.assertTrue(all(row["candidate"] >= row["baseline"]
                            for row in record["new_adversarial_detection"].values()))
        self.assertTrue(all(row["candidate_blocks"]
                            for row in record["new_structured_fidelity"].values()))

    def test_historical_judge_record_is_well_formed_and_linked(self):
        record = json.loads((ROOT / "bench" / "replication.json").read_text())
        totals = {method: record["run1"][method] + record["run2"][method]
                  for method in record["run1"]}
        self.assertEqual(sum(totals.values()), 100)
        self.assertLessEqual(record["agreement_count"], record["agreement_items"])
        lo, hi = record["zero_slop_pooled"]["wilson_95_ci"]
        self.assertLess(lo, record["zero_slop_pooled"]["selections"] / 100, hi)
        self.assertIn("[`bench/README.md`](bench/README.md)",
                      (ROOT / "README.md").read_text())

    def test_external_model_record_is_well_formed_and_documented(self):
        result = json.loads((ROOT / "bench" / "external-models" / "results.json").read_text())
        readme = re.sub(r"\s+", " ", (ROOT / "README.md").read_text())
        bench_readme = (ROOT / "bench" / "README.md").read_text()
        self.assertRegex(result["source"]["commit"], r"^[0-9a-f]{40}$")
        self.assertGreater(result["sample"]["preserved_generations"], 10000)
        self.assertEqual([row["rank"] for row in result["models"]],
                         list(range(1, len(result["models"]) + 1)))
        self.assertIn("Slop Index", bench_readme)
        self.assertIn("bench/README.md", readme)

    def test_readme_links_the_paired_audit_without_repeating_its_table(self):
        result = json.loads((ROOT / "bench" / "beemo-corpus" / "results.json").read_text())
        readme = (ROOT / "README.md").read_text()
        self.assertRegex(result["source"]["revision"], r"^[0-9a-f]{12,40}$")
        self.assertIn("Beemo", readme)
        self.assertIn("bench/README.md", readme)


class BeemoCorpusAudit(unittest.TestCase):
    """The paired external audit stays pinned, aggregate-only, and caveated."""

    ROOT = ROOT / "bench" / "beemo-corpus"

    def test_committed_result_contract(self):
        pin = json.loads((self.ROOT / "source.json").read_text())
        result = json.loads((self.ROOT / "results.json").read_text())
        self.assertEqual(result["result_kind"], "external_paired_edit_surface_audit")
        self.assertFalse(result["calibrated_accuracy"])
        self.assertEqual(result["source"]["revision"], pin["revision"])
        self.assertEqual(result["source"]["rows"], pin["expected_rows"])
        self.assertEqual(len(result["source"]["content_sha256"]), 64)
        for field in ("model_output", "human_edits", "human_output"):
            self.assertEqual(result["groups"][field]["documents"], pin["expected_rows"])

    def test_source_text_is_not_redistributed(self):
        shipped = [p.name for p in self.ROOT.iterdir() if p.is_file()]
        self.assertEqual(set(shipped), {"README.md", "audit.py", "results.json", "source.json"})
        self.assertFalse(any((self.ROOT / name).suffix in {".csv", ".parquet", ".jsonl"}
                             for name in shipped))

    def test_offline_contract_check(self):
        result = run([str(self.ROOT / "audit.py"), "--check"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fetch_failure_is_clean_and_actionable(self):
        spec = importlib.util.spec_from_file_location(
            "beemo_audit_test", self.ROOT / "audit.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        error = io.StringIO()
        with (mock.patch.object(sys, "argv", ["audit.py", "--fetch", "--check"]),
              mock.patch.object(module, "fetch_rows",
                                side_effect=RuntimeError("rate limited")),
              contextlib.redirect_stderr(error)):
            result = module.main()
        self.assertEqual(result, 2)
        self.assertIn("beemo audit: rate limited", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


class RaidPlusCorpusAudit(unittest.TestCase):
    """The current-model RAID+ audit is pinned, aggregate-only, and cannot be
    presented as slop quality or authorship accuracy."""

    ROOT = ROOT / "bench" / "raid-plus-corpus"

    def test_committed_result_contract(self):
        pin = json.loads((self.ROOT / "source.json").read_text())
        result = json.loads((self.ROOT / "results.json").read_text())
        self.assertEqual(result["result_kind"], "current_model_surface_audit")
        self.assertFalse(result["calibrated_accuracy"])
        self.assertEqual(result["source"]["revision"], pin["revision"])
        self.assertEqual(result["source"]["rows"], 8000)
        self.assertEqual(len(result["source"]["content_sha256"]), 64)
        self.assertEqual(result["source"]["model_rows"], pin["expected_models"])
        self.assertEqual(
            sum(row["documents"] for row in result["models"].values()),
            result["source"]["scored_rows"],
        )
        for model, row in result["models"].items():
            self.assertEqual(
                row["documents"] + row["failed_or_empty"],
                pin["expected_models"][model],
            )
        self.assertIn("not slop-quality labels", result["limits"].lower())

    def test_source_text_is_not_redistributed(self):
        shipped = {path.name for path in self.ROOT.iterdir() if path.is_file()}
        self.assertEqual(shipped, {"README.md", "audit.py", "results.json", "source.json"})
        self.assertFalse(any(
            path.suffix in {".csv", ".parquet", ".jsonl"}
            for path in self.ROOT.iterdir()
        ))

    def test_offline_contract_check(self):
        result = run([str(self.ROOT / "audit.py"), "--check"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_readme_and_chart_use_the_committed_result(self):
        result = json.loads((self.ROOT / "results.json").read_text())
        readme = (ROOT / "README.md").read_text().replace("**", "")
        labels = {
            "deepseek-v3": "DeepSeek V3",
            "gemini-3.1-pro": "Gemini 3.1 Pro",
            "gemma-3-27b": "Gemma 3 27B",
            "llama-3.3-70b": "Llama 3.3 70B",
        }
        for model, label in labels.items():
            row = result["models"][model]
            expected = (
                f"| {label} | {row['documents']:,} | "
                f"{row['mean_writing_score']:.1f} | "
                f"{row['at_or_above_generic_gate_pct']:.1f}% |"
            )
            with self.subTest(model=model):
                self.assertIn(expected, readme)
        chart = json.loads((ROOT / "bench" / "chart-data.json").read_text())
        self.assertEqual(len(chart["raid_plus_surface"]), 4)
        self.assertTrue((ROOT / "assets" / "bench-raid-plus.png").exists())

    def test_fetch_failure_is_clean_and_actionable(self):
        spec = importlib.util.spec_from_file_location(
            "raid_plus_audit_test", self.ROOT / "audit.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        error = io.StringIO()
        with (mock.patch.object(sys, "argv", ["audit.py", "--fetch", "--check"]),
              mock.patch.object(module, "fetch_rows",
                                side_effect=RuntimeError("rate limited")),
              contextlib.redirect_stderr(error)):
            result = module.main()
        self.assertEqual(result, 2)
        self.assertIn("RAID+ audit: rate limited", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())

    def test_fetch_retries_transient_server_errors(self):
        import urllib.error
        spec = importlib.util.spec_from_file_location(
            "raid_plus_retry_test", self.ROOT / "audit.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        transient = urllib.error.HTTPError(
            "https://example.invalid/rows", 502, "Bad Gateway", {}, None
        )
        response = io.StringIO('{"ok": true}')
        with (mock.patch.object(module.urllib.request, "urlopen",
                                side_effect=[transient, response]),
              mock.patch.object(module.time, "sleep") as sleep):
            self.assertEqual(module.fetch_json("https://example.invalid/rows", attempts=2),
                             {"ok": True})
        sleep.assert_called_once()


class QualityCorpus(unittest.TestCase):
    """Blind slop-quality labels stay method-hidden, split-safe, and auditable."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        rows = [
            ("q001", "s1", "dev", "email", "original",
             "Replica lag fell below ten seconds after the index rebuild."),
            ("q002", "s2", "test", "linkedin", "original",
             "We're beyond excited to announce a groundbreaking journey that "
             "will seamlessly unlock unprecedented value. Let's dive in."),
            ("q003", "s3", "dev", "blog", "zero-slop",
             "The cache cut median response time from 240 ms to 90 ms."),
            ("q004", "s4", "test", "newsletter", "humanizer",
             "In today's fast-paced landscape, this powerful shift serves as a "
             "testament to innovation and meaningful impact."),
        ]
        self.manifest = self.tmp / "manifest.json"
        manifest = {
            "schema": 1,
            "corpus_kind": "blind_slop_quality_panel",
            "label_protocol_sha256": "a" * 64,
            "items": [{"id": item_id, "source_id": source_id, "split": split,
                       "genre": genre, "method": method, "text": text,
                       "text_sha256": learn.text_sha256(text)}
                      for item_id, source_id, split, genre, method, text in rows],
        }
        self.manifest.write_text(json.dumps(manifest))
        labels = {
            "q001": ("clean", 1), "q002": ("sloppy", 5),
            "q003": ("clean", 1), "q004": ("sloppy", 4),
        }
        self.label_paths = []
        for rater in ("rater-a", "rater-b"):
            path = self.tmp / f"{rater}.json"
            path.write_text(json.dumps({
                "schema": 1, "rater": rater, "protocol_sha256": "a" * 64,
                "items": [{"id": item_id, "label": label, "severity": severity,
                           "signals": ["canned_framing"] if label == "sloppy" else []}
                          for item_id, (label, severity) in labels.items()],
            }))
            self.label_paths.append(path)
        self.result = self.tmp / "results.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_blind_packet_contains_no_method_source_split_or_score(self):
        result = run([str(QUALITY_PACKET), str(self.manifest)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        packet = json.loads(result.stdout)
        self.assertEqual(set(packet), {"schema", "protocol_sha256", "items"})
        for item in packet["items"]:
            self.assertEqual(set(item), {"id", "text"})

    def test_evaluation_computes_split_metrics_and_method_summary(self):
        args = [str(QUALITY_EVAL), "--manifest", str(self.manifest)]
        for label in self.label_paths:
            args += ["--labels", str(label)]
        result = run([*args, "--out", str(self.result), "--write"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(self.result.read_text())
        self.assertEqual(report["result_kind"], "blind_slop_quality_evaluation")
        self.assertFalse(report["calibrated_field_accuracy"])
        self.assertEqual(report["labels"]["consensus_items"], 4)
        self.assertEqual(report["splits"]["dev"]["items"], 2)
        self.assertEqual(report["splits"]["test"]["items"], 2)
        self.assertEqual(set(report["methods"]), {"original", "zero-slop", "humanizer"})
        self.assertGreaterEqual(report["surface_meter"]["accuracy"], 0.75)
        research = report["contextual_research_ablation"]["held_out_test_mean"]
        self.assertEqual(research["contextual_accuracy"], 1.0)
        self.assertGreaterEqual(research["contextual_minus_surface_accuracy"], 0.0)
        self.assertFalse(report["contextual_research_ablation"]["field_accuracy"])

    def test_evaluation_rejects_hash_drift_label_gaps_and_source_split_leakage(self):
        manifest = json.loads(self.manifest.read_text())
        manifest["items"][0]["text"] += " changed"
        self.manifest.write_text(json.dumps(manifest))
        result = run([str(QUALITY_PACKET), str(self.manifest)])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

        manifest["items"][0]["text_sha256"] = learn.text_sha256(
            manifest["items"][0]["text"])
        manifest["items"][1]["source_id"] = manifest["items"][0]["source_id"]
        self.manifest.write_text(json.dumps(manifest))
        result = run([str(QUALITY_PACKET), str(self.manifest)])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

    def test_committed_panel_and_results_are_current(self):
        built = run([str(QUALITY_BUILD), "--check"])
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        args = [str(QUALITY_EVAL), "--manifest", str(QUALITY_ROOT / "manifest.json")]
        for name in ("labels-rater-a.json", "labels-rater-b.json"):
            args += ["--labels", str(QUALITY_ROOT / name)]
        evaluated = run([*args, "--out", str(QUALITY_ROOT / "results.json"), "--check"])
        self.assertEqual(evaluated.returncode, 0,
                         evaluated.stdout + evaluated.stderr)
        report = json.loads((QUALITY_ROOT / "results.json").read_text())
        self.assertEqual(report["source"]["items"], 72)
        self.assertEqual(report["source"]["source_drafts"], 12)
        self.assertFalse(report["calibrated_field_accuracy"])


class CorpusAdmission(unittest.TestCase):
    """Every proposed corpus gets a documented, label-matched admission decision."""

    def test_registry_contract_and_requested_source_coverage(self):
        result = run([str(CORPUS_REGISTRY)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        registry = json.loads((ROOT / "bench" / "corpus-registry.json").read_text())
        self.assertIn("No listed corpus currently clears every requirement",
                      registry["policy"]["rule"])
        authorship_only = {"raid", "mage", "hc3", "arb", "editlens",
                           "maga-bench", "m4gt-bench", "coling-2025-mgt",
                           "m4", "autextification"}
        rows = {row["id"]: row for row in registry["datasets"]}
        for corpus_id in authorship_only:
            with self.subTest(corpus_id):
                self.assertNotEqual(rows[corpus_id]["tier"], "release_gate")
                self.assertNotEqual(rows[corpus_id]["status"], "measured")


class FeatureAblation(unittest.TestCase):
    """The old-versus-new claim stays tied to live data and one production path."""

    def test_committed_ablation_is_current_and_caveated(self):
        result = run([str(FEATURE_ABLATION)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((ROOT / "bench" / "feature-ablation" / "results.json").read_text())
        surface = report["deterministic_surface_ablation"]
        self.assertFalse(surface["exactly_unchanged"])
        self.assertGreater(surface["blind_quality_consensus_accuracy_candidate"],
                           surface["blind_quality_consensus_accuracy_baseline"])
        self.assertGreater(surface["accuracy_change_percentage_points"], 0)
        self.assertFalse(report["structured_contextual_research"]["field_accuracy"])
        self.assertIsNone(report["reason_labelled_retrieval"]["accuracy_result"])
        self.assertEqual(report["candidate"]["production_path"], "single")


class AIStoryHubCorpusAudit(unittest.TestCase):
    """External taxonomy coverage stays reproducible without bundling it."""

    SCRIPT = ROOT / "bench" / "aistoryhub-corpus" / "audit.py"
    PIN = ROOT / "bench" / "aistoryhub-corpus" / "source.json"
    RESULT = ROOT / "bench" / "aistoryhub-corpus" / "results.json"

    def test_committed_result_is_labeled_as_coverage_not_accuracy(self):
        result = json.loads(self.RESULT.read_text())
        self.assertEqual(result["audit_kind"], "external_taxonomy_probe_coverage")
        self.assertFalse(result["calibrated_accuracy"])
        hard = result["probe"]["by_lifecycle"]["hard_evidence"]
        self.assertEqual(hard["surface_rule_hit"], hard["testable"])
        guard = result["false_positive_guard"]
        self.assertEqual(guard["passes"], guard["documents"])

    def test_source_is_pinned_but_not_redistributed(self):
        pin = json.loads(self.PIN.read_text())
        self.assertEqual(pin["version"], "1.8")
        self.assertEqual(pin["entry_count"], 758)
        self.assertRegex(pin["sha256"], r"\A[0-9a-f]{64}\Z")
        self.assertFalse(
            (ROOT / "bench" / "aistoryhub-corpus" / "ai-cliches-corpus.json").exists()
        )

    def test_local_source_write_and_hash_mismatch_fail_closed(self):
        document = {
            "version": "test-1",
            "generated": "2026-08-22",
            "entry_count": 1,
            "entries": [{
                "term": "delve",
                "category": "Words & phrases",
                "category_key": "words_and_phrases",
                "confidence": "red",
                "lifecycle": "live",
                "strength_score": 99,
                "example": None,
            }],
        }
        raw = json.dumps(document, separators=(",", ":")).encode()
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.json"
            pin = root / "pin.json"
            output = root / "result.json"
            source.write_bytes(raw)
            pin.write_text(json.dumps({
                "source_url": "https://example.invalid/corpus.json",
                "version": document["version"],
                "generated": document["generated"],
                "entry_count": 1,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }))
            result = run([
                str(self.SCRIPT), "--source", str(source), "--pin", str(pin),
                "--output", str(output), "--write", "--show-misses", "0",
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            source.write_bytes(raw + b"\n")
            result = run([
                str(self.SCRIPT), "--source", str(source), "--pin", str(pin),
                "--output", str(output), "--check", "--show-misses", "0",
            ])
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)

    def test_empty_pin_strings_fail_closed(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("aistoryhub_audit", self.SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        pin = json.loads(self.PIN.read_text())
        pin["source_url"] = "   "
        with self.assertRaises(ValueError):
            module.validate_pin(pin)


class PortfolioDiagnostic(unittest.TestCase):
    """Batch templating is reported without changing the single-text score."""

    def test_repeated_openings_and_templates_are_found(self):
        docs = [
            ("a", "In today's rapidly evolving market, teams need a clear plan for delivery."),
            ("b", "In today's rapidly evolving market, teams need a clear plan for hiring."),
            ("c", "In today's rapidly evolving market, teams need a clear plan for pricing."),
            ("d", "The release failed because the queue filled overnight."),
        ]
        result = slopscore.portfolio_metrics(docs)
        self.assertTrue(result["measured"])
        self.assertEqual(result["repeated_openers"][0]["document_count"], 3)
        self.assertEqual(result["repeated_openers"][0]["text"],
                         "in today's rapidly evolving market")
        self.assertTrue(result["shared_phrases"])
        self.assertNotIn("in today's rapidly evolving market",
                         {row["text"] for row in result["shared_phrases"]})
        self.assertFalse(result["calibrated_probability"])

    def test_portfolio_abstains_on_too_few_drafts(self):
        result = slopscore.portfolio_metrics([("a", "One draft."), ("b", "Two drafts.")])
        self.assertFalse(result["measured"])
        self.assertIn("at least 3", result["reason"])

    def test_duplicate_document_names_are_rejected(self):
        with self.assertRaises(ValueError):
            slopscore.portfolio_metrics([("same", "First draft."),
                                         ("same", "Second draft."),
                                         ("third", "Third draft.")])


class ShapeDiagnostic(unittest.TestCase):
    """Excluded structure cannot leak back into the social-post shape verdict."""

    def test_short_bullets_do_not_manufacture_a_fragment_run(self):
        prose = [
            f"Paragraph {i} explains the release in enough detail for a reader to follow it."
            for i in range(8)
        ]
        text = "\n\n".join(prose + ["- Cut now.", "- Ship soon.", "- Read twice."])
        result = slopscore.shape_metrics(text, genre="social")
        self.assertTrue(result["measured"])
        self.assertEqual(result["max_fragment_run"], 0)
        self.assertFalse(result["broetry"])


class Fidelity(unittest.TestCase):
    """The channel the gate was missing. Benchmarking ranked the skill last on
    fidelity and it carried the only fabrication flag, because nothing measured
    it."""

    SRC = ("Acme raised $4.2M led by Basis Ventures. Setup time fell 40%. "
           "See https://acme.io/blog for the numbers.")

    def test_faithful_rewrite_passes(self):
        same = ("Acme raised $4.2M, led by Basis Ventures. Setup time fell 40%. "
                "The numbers are at https://acme.io/blog.")
        r = slopscore.fidelity(self.SRC, same)
        self.assertTrue(r["preserved"], "a faithful rewrite was marked lossy")
        self.assertFalse(r["invented"])

    def test_dropped_figure_is_caught(self):
        lossy = "Acme raised money led by Basis Ventures. See https://acme.io/blog."
        self.assertFalse(slopscore.fidelity(self.SRC, lossy)["preserved"])

    def test_invented_name_is_caught(self):
        made_up = (self.SRC + " Priya said it was the best quarter yet.")
        self.assertTrue(slopscore.fidelity(self.SRC, made_up)["invented"],
                        "an invented name slipped through")

    def test_invented_figure_is_caught(self):
        made_up = self.SRC.replace("40%", "40% and churn fell 12%")
        self.assertTrue(slopscore.fidelity(self.SRC, made_up)["invented"])

    def test_sentence_openers_are_not_entities(self):
        """'The', 'See', 'This' are not names; treating them as facts would
        make every rewrite look lossy."""
        r = slopscore.fidelity("The system works. See the docs.",
                               "It works. Read the docs.")
        self.assertTrue(r["preserved"])
        self.assertFalse(r["invented"])

    def test_ordered_list_markers_are_not_figures(self):
        before = "Three points:\n1. Keep the fact.\n2. Cut filler.\n3. Read it aloud."
        after = "Three points: keep the fact, cut filler, and read it aloud."
        r = slopscore.fidelity(before, after)
        self.assertTrue(r["preserved"])
        self.assertFalse(r["invented"])

    def test_common_corpus_openers_are_not_names(self):
        before = ("Welcome back. Artificial intelligence is changing. "
                  "Despite the limits, researchers continue. Bookmark this. "
                  "Unpopular opinion: the test helps.")
        after = ("AI is changing. Researchers continue despite the limits. "
                 "Save this. The test helps.")
        r = slopscore.fidelity(before, after)
        self.assertTrue(r["preserved"])
        self.assertFalse(r["invented"])

    def test_partial_entity_rename_is_caught(self):
        result = slopscore.fidelity("Basis Ventures led the round.",
                                   "Basis Labs led the round.")
        self.assertFalse(result["preserved"])
        self.assertTrue(result["invented"])

    def test_common_title_case_run_is_not_an_entity(self):
        result = slopscore.fidelity("Shipped Tuesday.",
                                   "Tuesday was the ship date.")
        self.assertTrue(result["preserved"])
        self.assertFalse(result["invented"])

    def test_interior_paraphrases_are_canonicalized(self):
        pairs = [
            ("I was very nervous.", "I felt extremely nervous."),
            ("We recalled the launch.", "We remembered the launch."),
        ]
        for before, after in pairs:
            with self.subTest(after=after):
                result = slopscore.fidelity(before, after)
                self.assertFalse(result["invented"], result)

    # Rates over a battery, not sentence-by-sentence. A regression is a change
    # in the aggregate, which is how you tell a real drop from a noisy example.
    FAITHFUL = [
        ("The service felt sluggish under load.", "Under load, the service felt sluggish."),
        ("Revenue rose 12%.", "Revenue was up 12 percent."),
        ("Ana Reyes joined as CTO.", "Ana Reyes is our new CTO."),
        ("The API returns JSON.", "It returns JSON."),
        ("The report covers Q3.", "This covers Q3."),
        ("Latency dropped after the index.", "After the index, latency dropped."),
        ("The exam felt familiar.", "It felt familiar, that exam."),
        ("Built the parser in Rust.", "Made the parser in Rust."),
        ("Basis Ventures led the round.", "The round was led by Basis Ventures."),
        # A spelled-out number is the same fact as its digits.
        ("It took 18 months to ship.", "It took eighteen months to ship."),
        # Sentence-opening common words and gerunds are not invented entities.
        ("Start with the schema.", "Begin with the schema, then wire the rest."),
        ("Reviewing the logs caught it.", "It surfaced while reviewing the logs."),
    ]
    INVENTED = [
        ("I passed the exam.", "I passed the exam. It felt surreal to see the score."),
        ("We raised a round.", "We raised a round. I was terrified we wouldn't close it."),
        ("The migration finished.", "The migration finished. My stomach was in knots."),
        ("I sat the exam in March.", "I sat the exam. By test day the real thing felt familiar."),
        ("Acme shipped it.", "Acme shipped it. Priya led the team."),
        ("Revenue rose.", "Revenue rose 40% last quarter."),
        ("We closed the deal.", "We closed the deal with Vertex on Friday."),
        # The precision fixes must not blind the check to a real invented name.
        ("The team shipped it.", "The team shipped it. Marcus wrote the parser."),
    ]

    def test_number_words_and_openers_are_faithful(self):
        """The two false-positive classes the token check used to invent:
        a number spelled out, and a common word capitalised at a sentence
        start. Neither is a dropped or invented fact."""
        for a, b in [("It took 18 months.", "It took eighteen months."),
                     ("Draw the diagram.", "Start by drawing the diagram."),
                     ("Usually it works.", "It usually works."),
                     ("We saw plenty of churn.", "Plenty of churn showed up.")]:
            r = slopscore.fidelity(a, b)
            self.assertTrue(r["preserved"] and not r["invented"],
                            f"faithful paraphrase flagged: {b!r} -> {r}")

    def test_faithful_rewrites_are_not_flagged(self):
        """False-positive RATE on paraphrase, not one blessed sentence."""
        fp = [b for a, b in self.FAITHFUL
              if (r := slopscore.fidelity(a, b)) and (not r["preserved"] or r["invented"])]
        self.assertLessEqual(len(fp), 1,
                             f"{len(fp)}/{len(self.FAITHFUL)} faithful rewrites flagged: {fp}")

    def test_inventions_are_caught(self):
        """Miss RATE on inventions — dropped facts, added figures, added feelings."""
        missed = [b for a, b in self.INVENTED if not slopscore.fidelity(a, b)["invented"]]
        self.assertEqual(len(missed), 0, f"missed inventions: {missed}")

    def test_cli_exits_nonzero_on_invention(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "a.md").write_text(self.SRC)
        (d / "b.md").write_text(self.SRC + " Priya led the round.")
        r = run([str(SCORER), "--fidelity", str(d / "a.md"), str(d / "b.md")])
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_fenced_code_is_preserved_exactly(self):
        before = "Run this:\n\n```python\nprint('safe')\n```\n\nThen inspect the result."
        changed = before.replace("print('safe')", "print('changed')")
        result = slopscore.fidelity(before, changed)
        self.assertFalse(result["preserved"])
        self.assertTrue(any(row["code"] == "code-block-modified"
                            for row in result["structure"]))

    def test_frontmatter_is_preserved_exactly(self):
        before = "---\ntitle: Safe release\ndraft: false\n---\n\nThe release is ready."
        changed = before.replace("draft: false", "draft: true")
        result = slopscore.fidelity(before, changed)
        self.assertFalse(result["preserved"])
        self.assertTrue(any(row["code"] == "frontmatter-modified"
                            for row in result["structure"]))

    def test_blockquotes_are_preserved_but_may_move(self):
        before = "> Keep the writer's exact words.\n> Including this line.\n\nCommentary follows."
        moved = "Commentary comes first.\n\n> Keep the writer's exact words.\n> Including this line."
        changed = moved.replace("exact words", "main idea")
        self.assertTrue(slopscore.fidelity(before, moved)["preserved"])
        result = slopscore.fidelity(before, changed)
        self.assertFalse(result["preserved"])
        self.assertTrue(any(row["code"] == "blockquote-modified"
                            for row in result["structure"]))

    def test_table_content_is_preserved_while_alignment_may_change(self):
        before = "| Method | Result |\n|---|---:|\n| Zero Slop | 18/18 |"
        aligned = "| Method    | Result |\n| :-------- | -----: |\n| Zero Slop | 18/18 |"
        changed = aligned.replace("18/18", "17/18")
        self.assertTrue(slopscore.fidelity(before, aligned)["preserved"])
        result = slopscore.fidelity(before, changed)
        self.assertFalse(result["preserved"])
        self.assertTrue(any(row["code"] == "table-modified"
                            for row in result["structure"]))

    def test_inline_code_and_paths_are_preserved(self):
        before = "Run `calibrate.py --selftest` from ./scripts/calibrate.py before release."
        changed = "Run `calibrate.py` from ./scripts/check.py before release."
        result = slopscore.fidelity(before, changed)
        codes = {row["code"] for row in result["structure"]}
        self.assertFalse(result["preserved"])
        self.assertIn("inline-code-missing", codes)
        self.assertIn("path-missing", codes)

    def test_heading_hierarchy_is_preserved_but_wording_may_change(self):
        before = "# How it works\n\nText.\n\n## Private learning\n\nMore text."
        wording = "# The workflow\n\nText.\n\n## Learning from edits\n\nMore text."
        changed = wording.replace("## Learning", "### Learning")
        self.assertTrue(slopscore.fidelity(before, wording)["preserved"])
        result = slopscore.fidelity(before, changed)
        self.assertFalse(result["preserved"])
        self.assertTrue(any(row["code"] == "heading-level"
                            for row in result["structure"]))


class Personalization(unittest.TestCase):
    """A named scoring profile exempts known watchlist words without claiming
    to learn a writer's complete voice or changing anyone else's meter."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "voices").mkdir()
        (self.tmp / "voices" / "au.json").write_text(
            json.dumps({"keep": ["robust", "landscape", "leverage"], "mute": []}))
        self._h = slopscore.HOME
        slopscore.HOME = self.tmp

    def tearDown(self):
        slopscore.HOME = self._h
        shutil.rmtree(self.tmp, ignore_errors=True)

    TXT = "Elevate your robust brand across the evolving landscape to leverage growth."

    def test_profile_quiets_the_authors_own_words(self):
        base = slopscore.score_text(self.TXT, slopscore.load_patterns())["ai_likelihood"]
        mine = slopscore.score_text(self.TXT, slopscore.load_patterns(voice="au"))["ai_likelihood"]
        self.assertLess(mine, base - 20, f"profile did not quiet: {base} -> {mine}")

    def test_profile_does_not_leak_to_other_users(self):
        a = slopscore.score_text(self.TXT, slopscore.load_patterns())["ai_likelihood"]
        b = slopscore.score_text(self.TXT, slopscore.load_patterns(voice="nobody"))["ai_likelihood"]
        self.assertEqual(a, b, "a missing profile changed the meter")

    def test_profile_still_catches_real_slop(self):
        slop = "We're thrilled to announce a seamless cutting-edge synergy! Agree? #Grateful"
        s = slopscore.score_text(slop, slopscore.load_patterns(voice="au"))["ai_likelihood"]
        self.assertGreater(s, 70, "personalisation let genuine slop through")

    def test_zero_weight_term_produces_no_hit(self):
        r = slopscore.score_text(self.TXT, slopscore.load_patterns(voice="au"))
        muted = {"robust", "landscape", "leverage"}
        self.assertFalse([h for h in r["hits"] if h["name"] in muted],
                         "a muted term still recorded a hit")

    def test_profile_builder_records_only_existing_watchlist_words(self):
        sample = self.tmp / "sample.md"
        sample.write_text(
            "Robust systems matter. Quokka-lantern is a phrase I made up."
        )
        with contextlib.redirect_stdout(io.StringIO()):
            learn.build_voice("sample", sample)
        profile = json.loads((self.tmp / "voices" / "sample.json").read_text())
        self.assertIn("robust", profile["keep"])
        self.assertNotIn("quokka-lantern", profile["keep"])
        self.assertEqual(profile["mute"], [])

    def test_profile_contract_is_described_without_full_style_claims(self):
        readme = " ".join((ROOT / "README.md").read_text().lower().split())
        skill = " ".join((ROOT / "SKILL.md").read_text().lower().split())
        page = " ".join(
            (ROOT / "website" / "app" / "page.tsx").read_text().lower().split()
        )

        self.assertIn("existing watchlist words", readme)
        self.assertIn("selected by name", readme)
        self.assertIn("does not learn cadence, tone, or a complete writing style", readme)

        self.assertIn("existing lexicon and context-gated watchlist", skill)
        self.assertIn("only when scoring with `--voice <name>`", skill)
        self.assertIn("does not learn cadence, syntax, humor, tone", skill)
        self.assertNotIn("profile in `data/voices/`", skill)

        self.assertIn("existing watchlist words", page)
        self.assertIn("only when that profile is selected", page)
        self.assertIn("does not learn your voice or full writing style", page)
        self.assertNotIn("which habits belong to you", page)


class Diagram(unittest.TestCase):
    """The engine diagram is shipped documentation; overflow is a defect."""

    def test_competitor_capability_audit_is_pinned_and_caveated(self):
        """The README comparison must be reproducible and must not turn a
        repository feature audit into an effectiveness claim."""
        audit_path = ROOT / "bench" / "competitor-capabilities.json"
        self.assertTrue(audit_path.exists(), "competitor capability audit is missing")
        audit = json.loads(audit_path.read_text())
        self.assertEqual(
            audit["products"]["blader"]["commit"],
            "e2e92e7b4b8229253ed5c8e81dc65463fdeddda5",
        )
        self.assertEqual(
            audit["products"]["no_ai_slop"]["commit"],
            "d30eddb9e04562234f2070b5ee63ca4649d9a05e",
        )
        self.assertEqual(
            audit["products"]["unslop_text"]["commit"],
            "f7c4aefc2c797a66e55b49354a93917ab60d33ac",
        )
        self.assertEqual(
            audit["products"]["avoid_ai_writing"]["commit"],
            "40328bd292bc682d46010a6f9ac2cdbf4fb4ceca",
        )
        self.assertGreaterEqual(len(audit["capabilities"]), 10)
        for row in audit["capabilities"]:
            with self.subTest(row=row["id"]):
                self.assertEqual(row["zero_slop"], "native")
                self.assertIn(row["blader"], {"guided", "not_documented"})
                self.assertIn(row["no_ai_slop"], {"guided", "not_documented"})
                self.assertIn(
                    row["unslop_text"],
                    {"native", "guided", "not_documented"},
                )
                self.assertIn(
                    row["avoid_ai_writing"],
                    {"native", "guided", "not_documented"},
                )

        readme = (ROOT / "README.md").read_text()
        normalized_readme = " ".join(readme.lower().split())
        self.assertIn("assets/competitor-capabilities.png", readme)
        self.assertIn("not which tool writes better", normalized_readme)
        self.assertIn("[`bench/README.md`](bench/README.md)", readme)
        self.assertTrue((ROOT / "assets" / "competitor-capabilities.png").exists())

    def test_incumbent_catalog_has_a_complete_zero_slop_coverage_map(self):
        """Every editorial section in the pinned incumbent is either covered by
        a named Zero Slop stage or rejected with a tested safety rationale."""
        path = ROOT / "bench" / "incumbent-audit" / "category-map.json"
        self.assertTrue(path.exists(), "incumbent category map is missing")
        audit = json.loads(path.read_text())
        self.assertEqual(
            audit["incumbent"]["commit"],
            "40328bd292bc682d46010a6f9ac2cdbf4fb4ceca",
        )
        self.assertEqual(audit["incumbent"]["catalog_sections"], 65)
        self.assertEqual(len(audit["coverage"]), 65)
        self.assertEqual(len({row["section"] for row in audit["coverage"]}), 65)
        for row in audit["coverage"]:
            with self.subTest(section=row["section"]):
                self.assertIn(row["stage"], {
                    "scorer", "interpreter", "rewriter", "fact_gate",
                    "copy_desk", "read_aloud", "scope",
                })
                self.assertTrue(row["zero_slop_anchor"])
                self.assertNotEqual(row.get("status"), "gap")
        rejected = {row["feature"] for row in audit["deliberate_non_adoptions"]}
        self.assertEqual(rejected, {
            "automatic_genre_guessing",
            "authorship_probabilities",
            "ten_thousand_word_cutoff",
            "canned_voice_personas",
        })

    def test_benchmark_charts_are_current(self):
        """The README charts are computed from the benchmark data; a re-run or a
        scorer change that would move a bar fails until they are regenerated."""
        r = run([str(ROOT / "bench" / "make_charts.py"), "--check"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_dist_bundle_is_current(self):
        """The pasteable bundle is what ChatGPT and Codex users actually get."""
        r = run([str(ROOT / "scripts" / "build_bundle.py"), "--check"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_one_pager_pdf_is_current(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("optional reportlab dependency is not installed")
        r = run([str(ROOT / "scripts" / "build_onepager_pdf.py"), "--check"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_skill_zip_is_one_clean_skill(self):
        """The claude.ai upload zip must hold exactly one SKILL.md and no nested
        zip. Built fresh here so the test never depends on a committed artifact —
        the zip is a release asset, kept out of the source tree so the repo's own
        download does not contain a nested zip."""
        import zipfile, io, importlib.util
        spec = importlib.util.spec_from_file_location(
            "bsz", ROOT / "scripts" / "build_skill_zip.py")
        bsz = importlib.util.module_from_spec(spec); spec.loader.exec_module(bsz)
        names = zipfile.ZipFile(io.BytesIO(bsz.build_bytes())).namelist()
        skills = [n for n in names if n.endswith("SKILL.md")]
        self.assertEqual(len(skills), 1, f"zip must hold exactly one skill: {skills}")
        nested = [n for n in names if n.endswith((".zip", ".tar", ".gz"))]
        self.assertEqual(nested, [], f"zip must not contain a nested archive: {nested}")

    def test_plugin_mirror_is_current(self):
        r = run([str(ROOT / "scripts" / "build_plugin.py"), "--check"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_plugin_runtime_contains_only_runtime_modules(self):
        shipped = {p.name for p in (ROOT / "skills" / "zero-slop" / "scripts").glob("*.py")}
        self.assertEqual(shipped, {
            "calibrate.py", "learn.py", "predictability.py", "rerank.py",
            "safeio.py", "slopscore.py", "version_check.py",
        })
        self.assertFalse((ROOT / "skills" / "zero-slop" / "references" /
                          "contextual-signals.md").exists())

    def test_engine_svg_has_no_overflow(self):
        r = run([str(ROOT / "scripts" / "check_svg.py"),
                 str(ROOT / "assets" / "engine.svg")])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_demo_svg_has_no_overflow(self):
        r = run([str(ROOT / "scripts" / "check_svg.py"),
                 str(ROOT / "assets" / "demo.svg")])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_svg_checker_handles_unnamespaced_overflow_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as td:
            overflow = Path(td) / "overflow.svg"
            overflow.write_text(
                '<svg viewBox="0 0 100 100"><text x="95" y="20">too wide</text></svg>'
            )
            result = run([str(ROOT / "scripts" / "check_svg.py"), str(overflow)])
            self.assertEqual(result.returncode, 1, result.stdout)
            relative = Path(td) / "relative.svg"
            relative.write_text(
                '<svg viewBox="0 0 100 100"><path class="ln" d="m 0 0 l 20 20"/></svg>'
            )
            result = run([str(ROOT / "scripts" / "check_svg.py"), str(relative)])
            self.assertEqual(result.returncode, 1, result.stdout)

    def test_engine_svg_names_both_operational_loops(self):
        src = (ROOT / "assets" / "engine.svg").read_text().lower()
        for phrase in (
                "seven roles", "one editing workflow", "editing workflow · seven roles",
                "1 · scorer", "2 · interpreter", "3 · rewriter", "4 · fact gate",
                "5 · copy desk", "6 · read aloud", "7 · verifier",
                "learn from the writer", "compare", "protect",
                "review", "4 · save", "reuse", "private writing rules",
                "helpful past fixes", "no neural training", "separate release review",
                "choose test sets", "independent review", "quality · safety · speed · cost",
                "people confirm the gain", "claude, gpt, or another compatible model",
                "your ai assistant"):
            with self.subTest(phrase):
                self.assertIn(phrase, src)
        for phrase in (
                "zero_slop_mode", "promotion-gated", "assisted",
                "surface score", "evidence", "fidelity", "corpora",
                "overlay", "diagnose", "operational loop", "production path"):
            with self.subTest(absent=phrase):
                self.assertNotIn(phrase, src)

    def test_production_docs_expose_no_experimental_feature_modes(self):
        for path in (ROOT / "README.md", ROOT / "SKILL.md",
                     ROOT / "assets" / "engine.svg"):
            source = path.read_text().lower()
            with self.subTest(path=path.name):
                self.assertNotIn("zero_slop_mode", source)
                self.assertNotIn("promotion-gated", source)
                self.assertNotIn("assisted mode", source)

    def test_engine_svg_is_theme_aware(self):
        src = (ROOT / "assets" / "engine.svg").read_text()
        self.assertIn("prefers-color-scheme", src)
        self.assertTrue(len(ET.fromstring(src).get("aria-label", "")) > 200,
                        "diagram needs a descriptive aria-label for screen readers")


class RerankBestOfN(unittest.TestCase):
    """Best-of-N selection: fidelity outranks cleanliness, always. A candidate
    that invents a fact must never win, even when it scores lower on the meter
    than a faithful-but-sloppier one."""

    ORIG = ("FlagShip raised a $4.2M seed led by Basis Ventures. "
            "Setup time fell 40% in 18 months.")

    def _rerank(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "rerank", ROOT / "scripts" / "rerank.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_invention_never_wins(self):
        cands = {
            "clean": ("FlagShip raised a $4.2M seed, led by Basis Ventures. "
                      "Setup time dropped 40% over eighteen months."),
            "invented": ("FlagShip raised a $4.2M seed, led by Basis Ventures. "
                         "Setup dropped 40% over eighteen months, and churn fell 12%."),
        }
        ranked = self._rerank().rank(self.ORIG, cands)
        self.assertNotEqual(ranked[0]["name"], "invented",
                            "a fabricated candidate won the rerank")
        self.assertTrue(ranked[-1]["invented"])

    def test_cleanest_faithful_wins(self):
        cands = {
            "sloppy": ("We are thrilled to announce that FlagShip raised a "
                       "game-changing $4.2M seed, led by the incredible team at "
                       "Basis Ventures. In a testament to our journey, setup time "
                       "fell 40% in 18 months."),
            "clean": ("FlagShip raised a $4.2M seed, led by Basis Ventures. "
                      "Setup time dropped 40% over eighteen months."),
        }
        ranked = self._rerank().rank(self.ORIG, cands)
        self.assertEqual(ranked[0]["name"], "clean",
                         "the cleaner faithful rewrite should win")

    def test_invalid_candidate_shapes_are_rejected(self):
        m = self._rerank()
        for candidates in ([], {"one": 7}, {"": "text"}):
            with self.subTest(candidates=candidates):
                with self.assertRaises(ValueError):
                    m.rank(self.ORIG, candidates)

    def test_cli_reports_missing_option_values_without_traceback(self):
        r = run([str(ROOT / "scripts" / "rerank.py"), "--original"])
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)


class PredictabilityChannel(unittest.TestCase):
    """The model channel: a deterministic cloze scaffold the harness model answers.
    The Python half must be reproducible and testable without any model."""

    def _mod(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "predictability", ROOT / "scripts" / "predictability.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    TEXT = ("The startup raised a substantial round from investors who believed in "
            "the mission. Revenue climbed steadily through the difficult quarter, and "
            "the founders stayed cautiously optimistic about the year ahead.")

    def test_probes_are_deterministic(self):
        m = self._mod()
        self.assertEqual(m.probes(self.TEXT, k=6), m.probes(self.TEXT, k=6))

    def test_perfect_and_zero(self):
        m = self._mod()
        pr = m.probes(self.TEXT, k=6)
        right = m.score(self.TEXT, {p["id"]: [p["answer"]] for p in pr}, k=6)
        wrong = m.score(self.TEXT, {p["id"]: ["zzzz"] for p in pr}, k=6)
        self.assertEqual(right["predictability"], 100.0)
        self.assertEqual(wrong["predictability"], 0.0)

    def test_morphology_counts_as_a_hit(self):
        m = self._mod()
        self.assertTrue(m._hit("raised", ["raise"]))
        self.assertTrue(m._hit("quickly", ["quick"]))
        self.assertFalse(m._hit("station", ["statue"]))

    def test_context_never_contains_the_answer(self):
        m = self._mod()
        for p in m.probes(self.TEXT, k=8):
            self.assertNotIn(p["answer"], m._norm(p["context"]).split())
            self.assertTrue(p["context"].endswith("___"))

    def test_only_three_guesses_count(self):
        m = self._mod()
        pr = m.probes(self.TEXT, k=1)
        guesses = {pr[0]["id"]: ["wrong", "stillwrong", "nope", pr[0]["answer"]]}
        self.assertEqual(m.score(self.TEXT, guesses, k=1)["predictability"], 0.0)

    def test_code_blocks_do_not_shift_probe_contexts(self):
        m = self._mod()
        text = ("A useful opening sentence.\n\n```python\nsecret_token = value\n```\n\n"
                "The service recovered quickly after the database restart.")
        probes = m.probes(text, k=4)
        self.assertTrue(probes)
        contexts = " ".join(p["context"] for p in probes)
        self.assertNotIn("secret_token", contexts)
        self.assertTrue(any("service" in p["context"].lower() or
                            "database" in p["context"].lower() for p in probes))

    def test_too_short_degrades_cleanly(self):
        m = self._mod()
        r = m.score("Hi there.", {}, k=6)
        self.assertIsNone(r["predictability"])

    def test_invalid_prediction_shapes_are_rejected(self):
        m = self._mod()
        for predictions in ([], {"bad-id": ["guess"]}, {"0": [7]},
                            {"999": ["guess"]}, {}):
            with self.subTest(predictions=predictions):
                with self.assertRaises(ValueError):
                    m.score(self.TEXT, predictions, k=2)

    def test_nonpositive_probe_count_is_rejected(self):
        m = self._mod()
        with self.assertRaises(ValueError):
            m.probes(self.TEXT, k=0)

    def test_cli_reports_missing_option_values_without_traceback(self):
        r = run([str(ROOT / "scripts" / "predictability.py"), "--score"])
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)


class CliStdin(unittest.TestCase):
    """The scorer reads stdin with no file argument and with the conventional '-',
    so it composes in a pipe without a temp file and never tracebacks on '-'."""

    SLOP = "I'm beyond excited to announce our game-changing platform"

    def test_stdin_with_no_arg(self):
        r = run([str(SCORER), "--explain"], stdin=self.SLOP)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Writing score", r.stdout)

    def test_dash_means_stdin(self):
        r = run([str(SCORER), "--explain", "-"], stdin=self.SLOP)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Writing score", r.stdout)


class VersionCheck(unittest.TestCase):
    """Version comparison is strict semver and the CLI rejects ambiguity."""

    def _mod(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "version_check", ROOT / "scripts" / "version_check.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_semver_parser_does_not_invent_components(self):
        module = self._mod()
        self.assertEqual(module._tuple("v2.4.10"), (2, 4, 10))
        self.assertEqual(module._tuple("2.4.2-beta.1"), (2, 4, 2))
        self.assertIsNone(module._tuple("2.4"))
        self.assertIsNone(module._tuple("release-2.4.2"))

    def test_unknown_and_conflicting_options_fail_before_network(self):
        script = ROOT / "scripts" / "version_check.py"
        for args in (["--unknown"], ["--quiet", "--json"]):
            with self.subTest(args=args):
                result = run([str(script), *args])
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2, buffer=False)
