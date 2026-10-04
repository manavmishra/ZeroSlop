"""Offline protocol and helper-equivalence checks; no model or host install."""
import io
import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mcp_local_tools as tools
import mcp_stdio as mcp
import reader_review
import register
import slopscore
import mcp_workflow_tools as workflow


def request(method, params=None, request_id=1):
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


INIT = request("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "offline-test", "version": "1"}})


class LocalMCP(unittest.TestCase):
    def setUp(self):
        self.server = mcp.Server()
        self.server.handle(INIT)
        self.text = "Ada shipped 12 tools. The release costs $8."

    def test_score_uses_existing_helper_without_note_or_network(self):
        with patch.object(slopscore, "HOME", Path("/nonexistent-zero-slop-test-home")):
            with patch("urllib.request.urlopen", side_effect=AssertionError("network")):
                expected = slopscore.score_text(self.text, slopscore.load_patterns())
                expected["shape"] = slopscore.shape_metrics(self.text)
                self.assertEqual(tools.call("score", {"text": self.text}), expected)

    def test_fidelity_normalizes_sets_and_preserves_gate(self):
        value = tools.call("fidelity", {"original": self.text, "rewrite": "Ada shipped 9 tools."})
        self.assertEqual(value, slopscore.fidelity(self.text, "Ada shipped 9 tools."))
        self.assertFalse(value["preserved"])
        self.assertTrue(value["invented"])
        json.loads(tools.encode(value))

    def test_register_equivalence_and_incomplete_answers_fail(self):
        self.assertEqual(tools.call("register_measure", {"text": self.text}), register.measure(self.text))
        self.assertEqual(tools.call("register_read", {"text": self.text}), register.read_packet(self.text, "supplied text"))
        self.assertEqual(tools.call("register_delta", {"original": self.text, "rewrite": "Ada shipped 12 tools."}), register.delta(self.text, "Ada shipped 12 tools."))
        result = tools.call("register_verdict", {"text": self.text, "answers": {}})
        self.assertNotEqual(result["exit_code"], 0)

    def test_reader_packets_match_and_default_retrospective(self):
        manifest = tools.call("reader_prepare", {"text": "First.\n\nPRIVATE FUTURE.", "audience": "Engineers"})
        self.assertEqual(manifest, reader_review.prepare("First.\n\nPRIVATE FUTURE.", "Engineers"))
        result = tools.call("reader_next", {"manifest": manifest, "reader": "R1"})
        self.assertEqual(result, reader_review.next_passage(manifest, "R1"))
        self.assertNotIn("PRIVATE FUTURE", json.dumps(result))
        self.assertEqual(result["context_mode"], "retrospective")
        self.assertEqual(tools.call("reader_skim", {"manifest": manifest}), reader_review.skim(manifest))

    def test_reader_recall_and_report_keep_existing_validation(self):
        manifest = reader_review.prepare("A grounded claim.", "Engineers")
        reviews = []
        for reader in ("R1", "R2"):
            reviews.append({"source_sha256": manifest["source_sha256"], "review_id": manifest["review_id"],
                            "reader": reader, "context_mode": "retrospective", "entries": [
                                {"note_id": reader + "-p1", "passage_id": "p1", "attention": "steady",
                                 "reaction": "The claim is clear.", "needed": "", "keep_reading": False}]})
        recall = {"manifest": manifest, "reader": "R1", "notes": reviews[0]}
        self.assertEqual(tools.call("reader_recall", recall), reader_review.recall(**recall))
        skim = {"source_sha256": manifest["source_sha256"], "review_id": manifest["review_id"],
                "context_mode": "retrospective", "reaction": "A clear opening.", "would_open": True}
        args = {"manifest": manifest, "reviews": reviews, "skim_review": skim}
        self.assertEqual(tools.call("reader_report", args), reader_review.report_data(**args))
        self.assertEqual(tools.call("reader_report", {**args, "format": "html"})["html"], reader_review.report(**args))
        args["reviews"] = reviews[:1]
        with self.assertRaises(tools.InputError):
            tools.call("reader_report", args)

    def test_result_size_error_never_returns_oversized_output(self):
        messages = [INIT, request("tools/call", {"name": "score", "arguments": {"text": self.text}}, 2)]
        output = io.BytesIO()
        with patch.object(tools, "call", return_value={"private": "x" * mcp.MAX_RESPONSE_BYTES}):
            mcp.serve(io.BytesIO(("\n".join(json.dumps(m) for m in messages) + "\n").encode()), output)
        responses = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(responses[1]["error"]["code"], -32603)
        self.assertLess(len(output.getvalue()), 2000)

    def test_rejects_path_command_unknown_learning_and_bad_types(self):
        for name, arguments in (("score", {"text": self.text, "path": "/etc/passwd"}), ("score", {"text": 1}), ("score", {"text": self.text, "formal": 1}), ("reader_prepare", {"text": self.text, "audience": "a" * 2001}), ("activate", {}), ("reflect", {}), ("shell", {"command": "id"})):
            with self.subTest(name=name), self.assertRaises(tools.InputError):
                tools.call(name, arguments)

    def test_bounds_unicode_depth_collections_and_text(self):
        nested = "x"
        for _ in range(15):
            nested = [nested]
        for value in (nested, [0] * (tools.MAX_ITEMS + 1), "x" * 20001, "\ud800", float("nan")):
            with self.subTest(value_type=type(value)), self.assertRaises(tools.InputError):
                tools.bounded(value)
        tools.bounded("é" * 20000)

    def test_initialize_and_list_actual_read_only_tools(self):
        result = mcp.Server().handle(INIT)["result"]
        self.assertEqual(result["serverInfo"]["version"], workflow.version_check.local_version())
        listed = self.server.handle(request("tools/list"))["result"]["tools"]
        self.assertEqual(listed, tools.TOOLS)
        self.assertTrue(all(t["annotations"]["readOnlyHint"] and not t["annotations"]["openWorldHint"] for t in tools.CORE_TOOLS))
        self.assertEqual({t["name"] for t in listed}, {t["name"] for t in tools.CORE_TOOLS + workflow.EXTRA_TOOLS})
        self.assertFalse(tools.tool_spec("learn_reflect")["annotations"]["readOnlyHint"])
        self.assertTrue(tools.tool_spec("version")["annotations"]["openWorldHint"])
        self.assertEqual(len({t["name"] for t in listed}), len(listed))

    def test_protocol_unknown_missing_init_and_notifications(self):
        self.assertEqual(mcp.Server().handle(request("tools/list"))["error"]["code"], -32002)
        self.assertEqual(self.server.handle(request("exec"))["error"]["code"], -32601)
        with patch.object(tools, "call", side_effect=AssertionError("notification executed")):
            self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "score", "arguments": {"text": self.text}}}))

    def test_errors_do_not_echo_private_text(self):
        private = "DO NOT ECHO PRIVATE INPUT"
        result = self.server.handle(request("tools/call", {"name": "score", "arguments": {"text": private, "path": private}}))
        self.assertEqual(result["error"]["code"], -32602)
        self.assertNotIn(private, json.dumps(result))

    def test_wire_parse_duplicate_keys_and_utf8_errors(self):
        for raw in (b'{"jsonrpc":"2.0","jsonrpc":"2.0"}\n', b'NaN\n', b'\xff\n', b'[]\n'):
            output = io.BytesIO()
            mcp.serve(io.BytesIO(raw), output)
            self.assertIn("error", json.loads(output.getvalue()))

    def test_wire_handshake_call_and_ping_are_json_only(self):
        messages = [INIT, request("tools/list", request_id=2), request("tools/call", {"name": "fidelity", "arguments": {"original": self.text, "rewrite": self.text}}, 3), request("ping", request_id=4)]
        output = io.BytesIO()
        mcp.serve(io.BytesIO(("\n".join(json.dumps(m) for m in messages) + "\n").encode()), output)
        responses = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([r["id"] for r in responses], [1, 2, 3, 4])
        self.assertTrue(json.loads(responses[2]["result"]["content"][0]["text"])["preserved"])

    def test_oversized_line_closes_without_processing_next(self):
        output = io.BytesIO()
        mcp.serve(io.BytesIO(b"x" * (mcp.MAX_MESSAGE_BYTES + 1) + b"\n" + json.dumps(INIT).encode() + b"\n"), output)
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], -32600)

    def test_formal_genre_voice_use_existing_helpers(self):
        with patch.object(slopscore, "HOME", Path("/nonexistent-zero-slop-test-home")):
            args = {"text": self.text, "formal": True, "genre": "social", "voice": "fixture"}
            expected = slopscore.score_text(self.text, slopscore.load_patterns(voice="fixture"), formal=True)
            expected["shape"] = slopscore.shape_metrics(self.text, genre="social")
            self.assertEqual(tools.call("score", args), expected)
        with self.assertRaises(ValueError):
            tools.call("score", {"text": self.text, "voice": "../outside"})

    def test_adjudication_uses_shared_source_bound_gate(self):
        original, rewrite = "It cost $8.", "It cost money."
        ruling = {"schema": 1, "original_sha256": hashlib.sha256(original.encode()).hexdigest(), "allow_dropped_figures": ["$8"]}
        allowed = slopscore.validate_adjudication(ruling, original)
        self.assertEqual(tools.call("fidelity", {"original": original, "rewrite": rewrite, "adjudication": ruling}), slopscore.fidelity(original, rewrite, allowed))
        ruling["original_sha256"] = "stale"
        with self.assertRaises(ValueError):
            tools.call("fidelity", {"original": original, "rewrite": rewrite, "adjudication": ruling})

    def test_finite_numbers_require_explicit_numeric_schema(self):
        tools.bounded(0.5, allow_floats=True)
        tools._validate_schema(0.5, {"type": "number", "minimum": 0, "maximum": 1})
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(tools.InputError):
                tools.bounded(value, allow_floats=True)
        for value, schema in ((0.5, {"type": "integer"}), (True, {"type": "number"}), ({"untyped": 0.5}, tools.OBJECT), (1.5, {"type": "number", "maximum": 1})):
            with self.assertRaises(tools.InputError):
                tools._validate_schema(value, schema)

    def test_const_true_consent_and_helper_systemexit_are_fail_closed(self):
        tools._validate_schema(True, {"type": "boolean", "const": True})
        for value in (False, 1, "true"):
            with self.assertRaises(tools.InputError):
                tools._validate_schema(value, {"type": "boolean", "const": True})
        with patch.object(tools, "call", side_effect=SystemExit("PRIVATE ERROR")):
            result = self.server.handle(request("tools/call", {"name": "score", "arguments": {"text": self.text}}))
            self.assertTrue(result["result"]["isError"])
            self.assertNotIn("PRIVATE ERROR", json.dumps(result))
            self.assertEqual(self.server.handle(request("ping"))["result"], {})

    def test_malformed_helper_result_cannot_crash_serializer(self):
        messages = [INIT, request("tools/call", {"name": "score", "arguments": {"text": self.text}}, 2), request("ping", request_id=3)]
        output = io.BytesIO()
        with patch.object(tools, "call", return_value={"broken": "\ud800"}):
            mcp.serve(io.BytesIO(("\n".join(json.dumps(m) for m in messages) + "\n").encode()), output)
        responses = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(responses[1]["error"]["code"], -32603)
        self.assertEqual(responses[2]["result"], {})

    def test_closed_extension_schema_validation_precedes_dispatch(self):
        cases = [("portfolio", {"documents": {}}), ("portfolio", {"documents": {str(i): "text" for i in range(21)}}),
                 ("portfolio", {"documents": {"label": 1}}), ("calibrate_compare", {"human": [], "ai": ["sample"]}),
                 ("learn_guide", {"text": self.text, "limit": 0}), ("learn_guide", {"text": self.text, "limit": 21}),
                 ("learn_guide", {"text": self.text, "limit": 1.5}), ("learn_guide", {"text": self.text, "reason": "unknown"}),
                 ("learn_reflect", {"produced": "draft", "shipped": "edit", "opt_in": False}),
                 ("learn_reflect", {"produced": "draft", "shipped": "edit", "opt_in": True, "activation_opt_in": False}),
                 ("learn_promote", {"opt_in": 1}), ("learn_voice", {"name": "profile", "sample": "sample", "opt_in": True, "path": "/etc/passwd"})]
        with patch.object(workflow, "call", side_effect=AssertionError("invalid input dispatched")):
            for name, args in cases:
                with self.subTest(name=name, args=args), self.assertRaises(tools.InputError):
                    tools.call(name, args)

    def test_registered_extension_dispatch_and_systemexit_boundary(self):
        with patch.object(workflow, "call", return_value={"test": 0.5}) as dispatch:
            self.assertEqual(tools.call("learn_guide", {"text": self.text, "limit": 2}), {"test": 0.5})
            dispatch.assert_called_once_with("learn_guide", {"text": self.text, "limit": 2})
        with patch.object(workflow, "call", side_effect=SystemExit("PRIVATE DETAIL")):
            with self.assertRaises(SystemExit):
                tools.call("learn_stats", {})
            result = self.server.handle(request("tools/call", {"name": "learn_stats", "arguments": {}}))
            self.assertTrue(result["result"]["isError"])
            self.assertNotIn("PRIVATE DETAIL", json.dumps(result))

    def test_keyboardinterrupt_is_not_swallowed(self):
        with patch.object(workflow, "call", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                tools.call("learn_stats", {})


class RealProcessMCP(unittest.TestCase):
    """Launch only the fixed local entrypoint with temporary private state.

    subprocess is a test harness dependency, never a runtime tool operation.
    """
    def run_wire(self, messages=None, raw=None, expected_files=()):
        if raw is None:
            raw = ("\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in messages) + "\n").encode()
        entrypoint = Path(__file__).resolve().parents[1] / "scripts" / "mcp_stdio.py"
        with tempfile.TemporaryDirectory(prefix="zs-mcp-test-") as private_state:
            process = subprocess.run([sys.executable, "-B", str(entrypoint)], input=raw,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
                                     env={"ZERO_SLOP_HOME": private_state, "ZERO_SLOP_NO_NOTES": "1", "ZS_NO_UPDATE_CHECK": "1"})
            self.assertEqual({item.name for item in Path(private_state).iterdir()}, set(expected_files))
            for name in expected_files:
                self.assertEqual((Path(private_state) / name).stat().st_mode & 0o777, 0o600)
        self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))
        self.assertEqual(process.stderr, b"")
        return [json.loads(line) for line in process.stdout.splitlines()]

    def test_surrogate_request_id_rejected_and_process_survives(self):
        for request_id in ("\ud800", "\udfff", "safe\ud800end"):
            invalid = json.dumps(request("ping", request_id=request_id)).encode()
            result = self.run_wire(raw=invalid + b"\n" + json.dumps(request("ping", request_id=2)).encode() + b"\n")
            self.assertEqual(result[0]["id"], None)
            self.assertEqual(result[0]["error"]["code"], -32600)
            self.assertEqual(result[1]["result"], {})

    def test_prepare_201_passages_roundtrips_intact(self):
        text = "\n\n".join("Passage " + str(i) + "." for i in range(201))
        producer = self.run_wire([INIT, request("tools/call", {"name": "reader_prepare", "arguments": {"text": text, "audience": "Engineers"}}, 2)])
        self.assertFalse(producer[1]["result"]["isError"])
        manifest = json.loads(producer[1]["result"]["content"][0]["text"])
        self.assertEqual(manifest["source"], text)
        self.assertEqual(len(manifest["passages"]), 201)
        consumer = self.run_wire([INIT, request("tools/call", {"name": "reader_next", "arguments": {"manifest": manifest, "reader": "R1"}}, 2), request("ping", request_id=3)])
        self.assertFalse(consumer[1]["result"]["isError"])
        packet = json.loads(consumer[1]["result"]["content"][0]["text"])
        self.assertEqual(packet["passage"]["text"], manifest["passages"][0]["text"])
        self.assertEqual(consumer[2]["result"], {})

    def test_20000_unicode_packet_rejected_before_unusable_manifest_returned(self):
        for text in ("😀" * 20000, "𐐀" * 20000):
            result = self.run_wire([INIT, request("tools/call", {"name": "reader_prepare", "arguments": {"text": text, "audience": "Engineers"}}, 2), request("ping", request_id=3)])
            self.assertTrue(result[1]["result"]["isError"])
            self.assertIn("not truncated", result[1]["result"]["content"][0]["text"])
            self.assertNotIn(text[:100], json.dumps(result[1]))
            self.assertEqual(result[2]["result"], {})

    def test_20000_ascii_text_roundtrip_remains_available(self):
        for text in ("a" * 20000, "é" * 20000, "\\\"" * 10000):
            producer = self.run_wire([INIT, request("tools/call", {"name": "reader_prepare", "arguments": {"text": text, "audience": "Engineers"}}, 2)])
            manifest = json.loads(producer[1]["result"]["content"][0]["text"])
            consumer = self.run_wire([INIT, request("tools/call", {"name": "reader_next", "arguments": {"manifest": manifest, "reader": "R1"}}, 2)])
            packet = json.loads(consumer[1]["result"]["content"][0]["text"])
            self.assertEqual(packet["passage"]["text"], text)

    def test_unknown_tool_returns_protocol_error_and_process_survives(self):
        result = self.run_wire([INIT, request("tools/call", {"name": "not_registered", "arguments": {}}, 2), request("ping", request_id=3)])
        self.assertEqual(result[1]["error"]["code"], -32602)
        self.assertNotIn("result", result[1])
        self.assertEqual(result[2]["result"], {})

    def test_supported_protocols_and_bounded_metadata_do_not_change_dispatch(self):
        for revision in mcp.PROTOCOLS:
            init = {**INIT, "params": {**INIT["params"], "protocolVersion": revision, "_meta": {"progressToken": "test"}}}
            result = self.run_wire([init, request("tools/list", {"_meta": {"progressToken": 1}}, 2), request("tools/call", {"name": "version", "arguments": {}, "_meta": {"untrusted": "ignored"}}, 3)])
            self.assertEqual(result[0]["result"]["protocolVersion"], revision)
            self.assertEqual(len(result[1]["result"]["tools"]), len(tools.TOOLS))
            version_result = json.loads(result[2]["result"]["content"][0]["text"])
            self.assertFalse(version_result["checked"])
            self.assertNotIn("ignored", json.dumps(result))

    def test_protocol_negotiation_falls_back_to_supported_handshake_revision(self):
        init = {**INIT, "params": {**INIT["params"], "protocolVersion": "not-supported"}}
        result = self.run_wire([init])
        self.assertEqual(result[0]["result"]["protocolVersion"], mcp.PROTOCOLS[-1])

    def test_learning_systemexit_redacted_and_private_state_unchanged(self):
        cases = [("learn_voice", {"name": "../outside", "sample": "We delve into details.", "opt_in": True}),
                 ("learn_reflect", {"produced": "A claim.", "shipped": "A claim.", "opt_in": True,
                                    "feedback": {"schema": 1, "source_sha256": "stale", "target_sha256": "stale", "edits": []}})]
        for name, arguments in cases:
            result = self.run_wire([INIT, request("tools/call", {"name": name, "arguments": arguments}, 2), request("ping", request_id=3)])
            self.assertTrue(result[1]["result"]["isError"])
            self.assertNotIn("outside", json.dumps(result))
            self.assertNotIn("stale", json.dumps(result))
            self.assertEqual(result[2]["result"], {})

    def test_unapproved_state_changes_rejected_by_protocol_before_any_write(self):
        for name, arguments in (("learn_promote", {"opt_in": False}),
                                ("learn_reflect", {"produced": "draft", "shipped": "edit", "opt_in": True, "activation_opt_in": False})):
            result = self.run_wire([INIT, request("tools/call", {"name": name, "arguments": arguments}, 2), request("ping", request_id=3)])
            self.assertEqual(result[1]["error"]["code"], -32602)
            self.assertEqual(result[2]["result"], {})

    def test_approved_reflection_is_private_without_automatic_activation(self):
        result = self.run_wire([INIT, request("tools/call", {"name": "learn_reflect", "arguments": {
            "produced": "An interesting ordinary observation remains in this draft.",
            "shipped": "The observation remains in this draft.", "opt_in": True}}, 2), request("ping", request_id=3)], expected_files=("reflections.json",))
        self.assertFalse(result[1]["result"]["isError"])
        reflected = json.loads(result[1]["result"]["content"][0]["text"])
        self.assertEqual(reflected["exit_code"], 0)
        self.assertNotIn("activation", reflected)
        self.assertEqual(result[2]["result"], {})


if __name__ == "__main__":
    unittest.main()
