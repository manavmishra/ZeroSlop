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
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
DATA = ROOT / "data"
CORPUS = DATA / "corpus" / "must-not-flag"
SCORER = ROOT / "scripts" / "slopscore.py"

import learn  # noqa: E402
import slopscore  # noqa: E402


def run(args, stdin=None):
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, input=stdin, cwd=str(ROOT))


def score(text):
    """AI-likelihood for a string, via the library path."""
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

    def test_human_corpus_stays_clean(self):
        """The false-positive floor. Every one of these is real human writing."""
        for f in sorted(CORPUS.glob("*.txt")):
            with self.subTest(f.name):
                self.assertLess(score(f.read_text()), 30,
                                f"{f.name} convicted as AI")

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
        for k in ("ai_likelihood", "burstiness", "n_words", "hits"):
            self.assertIn(k, d)

    def test_reads_stdin(self):
        r = run([str(SCORER)], stdin="A short honest sentence about nothing.")
        self.assertIn("AI-likelihood", r.stdout)

    def test_unicode_does_not_crash(self):
        r = run([str(SCORER)], stdin="Ünïcödé — emoji 🚀 中文 العربية\n")
        self.assertEqual(r.returncode, 0, r.stderr)


# --------------------------------------------------------------------------
class ReflectLoop(unittest.TestCase):
    """The learning path. Every test runs against a throwaway copy of data/."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(DATA, self.tmp / "data")
        self._save = (learn.DATA, learn.OBS, learn.CORPUS, learn.LOG)
        learn.DATA = self.tmp / "data"
        learn.OBS = learn.DATA / "reflections.json"
        learn.CORPUS = learn.DATA / "corpus" / "must-not-flag"
        learn.LOG = learn.DATA / "learned-log.md"
        if learn.OBS.exists():
            learn.OBS.unlink()

    def tearDown(self):
        learn.DATA, learn.OBS, learn.CORPUS, learn.LOG = self._save
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _pair(self, produced, shipped, doc):
        a, b = self.tmp / "p.md", self.tmp / "s.md"
        a.write_text(produced)
        b.write_text(shipped)
        learn.reflect(str(a), str(b), doc)

    def _obs(self):
        return json.loads(learn.OBS.read_text())["observations"]

    def _learned(self):
        return json.loads((learn.DATA / "learned.json").read_text())["patterns"]

    # -- recurrence ------------------------------------------------------
    def test_single_document_cannot_mint_a_pattern(self):
        """The poisoning guard: one writer's idiosyncratic cut is not a tell."""
        before = len(self._learned())
        self._pair("We shipped it. This moves the needle on latency for us.",
                   "We shipped it. Latency dropped.", "doc1")
        learn.promote(True, "test", 2.5)
        self.assertEqual(len(self._learned()), before)

    def test_promotes_only_after_threshold_documents(self):
        txt = "We shipped it. This moves the needle on latency for us."
        cut = "We shipped it. Latency dropped."
        for i in range(learn.PROMOTE_AT):
            self._pair(txt, cut, f"doc{i}")
        before = len(self._learned())
        learn.promote(True, "test", 2.5)
        minted = self._learned()[before:]
        # Names are digests now — the readable phrase is the author's prose and
        # must not enter a tracked file. Assert on behaviour: some minted
        # pattern matches the span that recurred.
        self.assertTrue(any(re.search(p["rx"], "this moves the needle on latency", re.I)
                            for p in minted),
                        f"the recurring tell was not minted: {[p['name'] for p in minted]}")

    def test_same_document_counted_once(self):
        """Re-running reflect on one doc must not inflate its way to threshold."""
        txt = "We shipped it. This moves the needle on latency for us."
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
        txt = "We shipped it. This moves the needle on latency for us."
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
        txt = "We shipped it. Quietly winding down enterprise sales was the call."
        cut = "We shipped it. That was the call."
        for i in range(learn.PROMOTE_AT):
            self._pair(txt, cut, f"doc{i}")
        learn.promote(True, "test", 2.5)
        blob = (learn.DATA / "learned.json").read_text().lower()
        for secret in ("quietly", "winding", "enterprise sales"):
            self.assertNotIn(secret, blob,
                             f"user prose {secret!r} leaked into a tracked file")

    def test_promotion_is_not_repeated(self):
        txt = "We shipped it. This moves the needle on latency for us."
        cut = "We shipped it. Latency dropped."
        for i in range(learn.PROMOTE_AT):
            self._pair(txt, cut, f"doc{i}")
        learn.promote(True, "test", 2.5)
        n = len(self._learned())
        learn.promote(True, "test", 2.5)
        self.assertEqual(len(self._learned()), n, "double-minted the same span")

    def test_learned_pattern_does_not_break_the_human_corpus(self):
        """After learning, the whole safety corpus must still score clean."""
        txt = "We shipped it. This moves the needle on latency for us."
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
            a.write_text("This moves the needle on latency. " * 800)
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
        m = re.search(r"\[`bench/`\]\(bench/\) average (\d+)",
                      re.sub(r"\s+", " ", self.docs["README.md"]))
        self.assertIsNotNone(m, "README no longer states the AI-draft anchor")
        self.assertAlmostEqual(int(m.group(1)), ai_mean, delta=2,
                               msg=f"README says drafts average {m.group(1)}, measured {ai_mean:.1f}")
        m2 = re.search(r"lands\s+between (\d+) and (\d+)",
                       re.sub(r"\s+", " ", self.docs["README.md"]))
        self.assertIsNotNone(m2, "README no longer states the human-writing anchor")
        c_lo, c_hi = int(m2.group(1)), int(m2.group(2))
        self.assertLessEqual(c_lo, lo, f"README floor {c_lo} above measured {lo:.1f}")
        self.assertGreaterEqual(c_hi, hi, f"README ceiling {c_hi} below measured {hi:.1f}")
        self.assertLess(c_hi - hi, 8, f"README ceiling {c_hi} overstates measured max {hi:.1f}")

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
        v = _j.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
        self.assertIn(f'version: "{v}"', self.docs["SKILL.md"],
                      "SKILL.md version does not match the plugin manifest")


class Diagram(unittest.TestCase):
    """The engine diagram is shipped documentation; overflow is a defect."""

    def test_dist_bundle_is_current(self):
        """The pasteable bundle is what ChatGPT and Codex users actually get."""
        r = run([str(ROOT / "scripts" / "build_bundle.py"), "--check"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_plugin_mirror_is_current(self):
        r = run([str(ROOT / "scripts" / "build_plugin.py"), "--check"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_engine_svg_has_no_overflow(self):
        r = run([str(ROOT / "scripts" / "check_svg.py"),
                 str(ROOT / "assets" / "engine.svg")])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_engine_svg_is_theme_aware(self):
        src = (ROOT / "assets" / "engine.svg").read_text()
        self.assertIn("prefers-color-scheme", src)
        self.assertTrue(len(ET.fromstring(src).get("aria-label", "")) > 200,
                        "diagram needs a descriptive aria-label for screen readers")


if __name__ == "__main__":
    unittest.main(verbosity=2, buffer=False)
