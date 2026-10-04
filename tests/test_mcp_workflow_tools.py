"""Text adapter parity, consent and privacy checks without paid calls or real state."""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calibrate
import learn
import mcp_local_tools as local
import mcp_workflow_tools as workflow
import predictability
import rerank
import rescue
import slopscore


class WorkflowAdapters(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="zs-mcp-workflow-")
        self.private = Path(self.temporary.name)
        self.context = contextlib.ExitStack()
        for module, attribute, value in (
            (learn, "HOME", self.private), (learn, "OBS", self.private / "reflections.json"),
            (learn, "LOCAL", self.private / "learned.json"),
            (learn, "LOCAL_LOG", self.private / "learned-log.md"),
            (slopscore, "HOME", self.private),
        ):
            self.context.enter_context(patch.object(module, attribute, value))
        self.context.enter_context(patch("urllib.request.urlopen", side_effect=AssertionError("network not allowed in this test")))
        self.text = "Ada shipped 12 tools. The team reviews them on Friday."

    def tearDown(self):
        self.context.close()
        self.temporary.cleanup()

    def call(self, name, args):
        return local.call(name, args)

    def test_heatmap_and_portfolio_match_existing_helpers(self):
        self.assertEqual(self.call("heatmap", {"text": self.text})["guide"], slopscore.render_heatmap(self.text, slopscore.load_patterns()))
        documents = {"A": self.text, "B": self.text, "C": self.text}
        self.assertEqual(self.call("portfolio", {"documents": documents}), slopscore.portfolio_metrics(documents.items()))
        self.assertEqual(list(self.private.iterdir()), [])

    def test_predictability_helpers_and_rescue_match(self):
        text = self.text * 20
        self.assertEqual(self.call("predictability_probes", {"text": text}), predictability.probes(text))
        predictions = {str(probe["id"]): ["fictional-guess"] for probe in predictability.probes(text)}
        self.assertEqual(self.call("predictability_score", {"text": text, "predictions": predictions}), predictability.score(text, predictions))
        with self.assertRaises(ValueError):
            self.call("predictability_score", {"text": text, "predictions": {}})
        result = self.call("rescue", {"text": self.text})
        self.assertEqual(result["text"], rescue.rescue_text(self.text))
        self.assertFalse(result["editorial_verification_complete"])

    def test_rerank_keeps_source_first_and_uses_same_gate(self):
        candidates = {"source": self.text, "invented": "Ada shipped 99 tools."}
        actual = self.call("rerank", {"original": self.text, "candidates": candidates})
        self.assertEqual(actual, rerank.rank(self.text, candidates))
        self.assertEqual(actual[0]["name"], "source")

    def test_adjudication_is_source_bound_and_other_gates_remain(self):
        ruling = {"schema": 1, "original_sha256": hashlib.sha256(self.text.encode()).hexdigest(), "allow_dropped_figures": ["12"]}
        args = {"original": self.text, "candidates": {"removed": "Ada shipped tools."}, "adjudication": ruling}
        actual = self.call("rerank", args)
        self.assertEqual(actual, rerank.rank(self.text, args["candidates"], adjudicated=slopscore.validate_adjudication(ruling, self.text)))
        ruling["original_sha256"] = "stale"
        with self.assertRaises(ValueError):
            self.call("rerank", args)

    def test_private_guidance_abstains_without_evidence(self):
        result = self.call("learn_guide", {"text": self.text})
        self.assertEqual(result["rewrite_preferences"], [])
        self.assertFalse(result["calibrated_probability"])
        self.assertEqual(list(self.private.iterdir()), [])

    def test_all_learning_writes_require_affirmative_opt_in(self):
        operations = {
            "learn_reflect": {"produced": self.text, "shipped": self.text},
            "learn_promote": {}, "learn_demote": {}, "learn_decay": {},
            "learn_voice": {"name": "writer", "sample": self.text},
            "learn_confirm": {"text": self.text},
        }
        for name, args in operations.items():
            for absent in (args, {**args, "opt_in": False}):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    self.call(name, absent)
            self.assertEqual(list(self.private.iterdir()), [])

    def test_reflect_stores_evidence_without_automatic_activation(self):
        result = self.call("learn_reflect", {"produced": "An interesting ordinary observation remains in this draft.", "shipped": "The observation remains in this draft.", "opt_in": True})
        self.assertEqual(result["exit_code"], 0)
        self.assertNotIn("python3", result["diagnostic"])
        self.assertTrue((self.private / "reflections.json").is_file())
        self.assertFalse((self.private / "learned.json").exists())
        self.assertNotIn("activation", result)
        self.assertEqual((self.private / "reflections.json").stat().st_mode & 0o777, 0o600)
        with patch.object(learn, "promote", return_value=0) as activate, patch.object(learn, "demote", return_value=0):
            self.call("learn_reflect", {"produced": self.text, "shipped": self.text, "opt_in": True, "activation_opt_in": True})
            activate.assert_called_once_with(True, "reflect-learned", learn.START_WEIGHT)

    def test_feedback_rejects_stale_hashes_before_private_evidence_write(self):
        payload = {"schema": 1, "source_sha256": "stale", "target_sha256": "stale", "edits": []}
        with self.assertRaises(SystemExit):
            self.call("learn_reflect", {"produced": self.text, "shipped": self.text, "opt_in": True, "feedback": payload})
        self.assertFalse((self.private / "reflections.json").exists())

    def test_voice_profile_selects_existing_terms_and_rejects_paths(self):
        result = self.call("learn_voice", {"name": "writer", "sample": "We delve into details.", "opt_in": True})
        self.assertEqual(result["exit_code"], 0)
        self.assertNotIn("python3", result["diagnostic"])
        self.assertIn("mcp__plugin_zero-slop_zero-slop-local__score", result["diagnostic"])
        profile = self.private / "voices" / "writer.json"
        data = json.loads(profile.read_text())
        self.assertIn("delve", data["keep"])
        self.assertEqual(profile.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(SystemExit):
            self.call("learn_voice", {"name": "../outside", "sample": self.text, "opt_in": True})

    def test_calibration_same_formula_without_activating_weights(self):
        human, ai = ["plain grounded prose " * 20], ["facilitate emphasize enhance " * 20]
        actual = self.call("calibrate_compare", {"human": human, "ai": ai})
        expected, hn, an = calibrate.excess_weights_from_texts(human, ai)
        self.assertEqual((actual["weights"], actual["human_words"], actual["ai_words"]), (expected, hn, an))
        self.assertFalse(actual["rules_activated"])
        self.assertFalse(actual["quality_accuracy_established"])
        self.assertEqual(list(self.private.iterdir()), [])

    def test_version_does_not_query_network_by_default(self):
        result = self.call("version", {})
        expected = json.loads((Path(__file__).resolve().parents[1] / "package.json").read_text())["version"]
        self.assertEqual(result["local"], expected)
        self.assertFalse(result["checked"])
        with patch.dict("os.environ", {"ZS_NO_UPDATE_CHECK": "1"}):
            self.assertFalse(self.call("version", {"check_for_updates": True})["checked"])

    def test_paths_and_unknown_fields_cannot_reach_helpers(self):
        for name, args in (
            ("portfolio", {"documents": {"A": 1}}),
            ("rerank", {"original": self.text, "candidates": {}, "path": "/etc/passwd"}),
            ("learn_guide", {"text": self.text, "limit": 21}),
            ("learn_reflect", {"produced": self.text, "shipped": self.text, "opt_in": True, "doc_id": "secret"}),
            ("learn_voice", {"name": "writer", "sample": self.text, "opt_in": True, "path": "/etc/passwd"}),
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.call(name, args)

    def test_fixed_registry_annotations_describe_side_effects(self):
        specs = {item["name"]: item for item in workflow.EXTRA_TOOLS}
        for name in ("learn_reflect", "learn_promote", "learn_demote", "learn_voice", "learn_confirm", "learn_decay"):
            self.assertFalse(specs[name]["annotations"]["readOnlyHint"])
            self.assertFalse(specs[name]["annotations"]["idempotentHint"])
            self.assertTrue(specs[name]["inputSchema"]["properties"]["opt_in"]["const"])
        self.assertTrue(specs["version"]["annotations"]["openWorldHint"])
        for name in ("learn_demote", "learn_voice", "learn_decay"):
            self.assertTrue(specs[name]["annotations"]["destructiveHint"])

    def test_printer_capture_is_bounded_and_declares_truncation(self):
        def printer():
            print("x" * 100000)
            return 0
        result = workflow._printed(printer)
        self.assertEqual(len(result["diagnostic"]), 65536)
        self.assertTrue(result["diagnostic_truncated"])

    def test_cli_followup_advice_routes_only_to_declared_tools(self):
        def printer():
            print("run: python3 scripts/calibrate.py --selftest")
            print("use it: python3 scripts/slopscore.py --voice fictional draft.md")
            print("Run --promote --apply to activate them locally, or use --auto-apply with --reflect.")
            return 0
        result = workflow._printed(printer)
        self.assertEqual(result["exit_code"], 0)
        for fragment in ("python3", "--promote", "--auto-apply"):
            self.assertNotIn(fragment, result["diagnostic"])
        for tool in ("calibrate_selftest", "score", "learn_promote"):
            self.assertIn("mcp__plugin_zero-slop_zero-slop-local__" + tool, result["diagnostic"])
        self.assertIn("separate affirmative human activation approval", result["diagnostic"])

    def test_real_process_voice_response_has_no_shell_followup(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "offline-test", "version": "1"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "learn_voice", "arguments": {
                "name": "fictional", "sample": "We delve into details.", "opt_in": True}}},
            {"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {}},
        ]
        env = dict(os.environ, ZERO_SLOP_HOME=str(self.private), ZS_NO_UPDATE_CHECK="1",
                   ZERO_SLOP_NO_NOTES="1", PYTHONDONTWRITEBYTECODE="1")
        run = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/mcp_stdio.py")],
                             input="\n".join(json.dumps(item) for item in messages) + "\n",
                             text=True, capture_output=True, env=env, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        responses = [json.loads(line) for line in run.stdout.splitlines()]
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        self.assertFalse(responses[1]["result"]["isError"])
        self.assertNotIn("python3", result["diagnostic"])
        self.assertIn("mcp__plugin_zero-slop_zero-slop-local__score", result["diagnostic"])
        self.assertEqual(responses[2]["result"], {})


if __name__ == "__main__":
    unittest.main()
