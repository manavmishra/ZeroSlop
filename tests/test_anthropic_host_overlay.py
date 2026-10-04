"""Offline host-profile isolation and complete instruction-routing checks."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_plugin
import build_marketplace_package as package
import mcp_local_tools
import mcp_workflow_tools


class AnthropicHostOverlay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.canonical = package.payload(ROOT)
        self.rules = json.loads((ROOT / build_plugin.ANTHROPIC_OVERLAY / "routing.json").read_bytes())
        # Real descriptors from the fixed adapters, never invented tool stubs.
        self.tools = list({tool["name"]: tool for tool in
                           mcp_local_tools.TOOLS + mcp_workflow_tools.EXTRA_TOOLS}.values())
        for name in build_plugin.MCP_RUNTIME:
            target = self.root / "scripts" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "scripts" / name, target)
        shutil.copytree(ROOT / build_plugin.ANTHROPIC_OVERLAY,
                        self.root / build_plugin.ANTHROPIC_OVERLAY)

    def overlay(self, **kwargs):
        return build_plugin.anthropic_payload(
            self.root, kwargs.get("files", self.canonical), kwargs.get("tools", self.tools))

    def test_portable_ten_module_set_and_npm_exclusions_are_explicit(self):
        names = {path.name for path in build_plugin.wanted(ROOT / "scripts")}
        self.assertTrue(build_plugin.MCP_RUNTIME.isdisjoint(names))
        self.assertEqual(len([name for name in names if name.endswith(".py")]), 10)
        self.assertTrue(build_plugin.MCP_RUNTIME.isdisjoint(build_plugin.EXCLUDE))
        npm = json.loads((ROOT / "package.json").read_bytes())["files"]
        for name in build_plugin.MCP_RUNTIME:
            self.assertIn("!scripts/" + name, npm)

    def test_complete_actual_inventory_is_required(self):
        self.assertEqual(set(self.rules["required_tools"]), {tool["name"] for tool in self.tools})
        for missing in self.rules["required_tools"]:
            with self.subTest(tool=missing), self.assertRaises(ValueError):
                self.overlay(tools=[tool for tool in self.tools if tool["name"] != missing])

    def test_invalid_duplicate_and_nonstring_descriptors_fail(self):
        for tools in (None, self.tools + [self.tools[0]], [{"name": []}], [{}]):
            with self.subTest(descriptors=type(tools)), self.assertRaises(ValueError):
                self.overlay(tools=tools)

    def test_folder_pairs_exact_remote_and_real_plugin_root_stdio(self):
        files = self.overlay()
        config = json.loads(files[".mcp.json"])["mcpServers"]
        self.assertEqual(config["zero-slop"], {"type": "http", "url": package.MCP_URL})
        self.assertEqual(config["zero-slop-local"], {
            "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/skills/zero-slop/scripts/mcp_stdio.py"]})
        for name in build_plugin.MCP_RUNTIME:
            self.assertEqual(files["skills/zero-slop/scripts/" + name],
                             (ROOT / "scripts" / name).read_bytes())

    def test_canonical_payload_and_openai_archive_are_byte_unchanged(self):
        before = copy.deepcopy(self.canonical)
        first = package.archive_bytes(self.canonical)
        self.overlay()
        self.assertEqual(self.canonical, before)
        self.assertEqual(package.archive_bytes(self.canonical), first)
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(json.loads(archive.read(".mcp.json")), {
                "mcpServers": {"zero-slop": {"type": "http", "url": package.MCP_URL}}})
            self.assertEqual(json.loads(archive.read(".codex-plugin/plugin.json"))["mcpServers"], "./.mcp.json")
            for name in build_plugin.MCP_RUNTIME:
                self.assertNotIn("skills/zero-slop/scripts/" + name, archive.namelist())
            self.assertEqual(archive.read(".claude-plugin/icon.svg"), self.canonical[".claude-plugin/icon.svg"])

    def test_only_routing_config_and_instruction_copies_change(self):
        files = self.overlay()
        for name, original in self.canonical.items():
            if name != ".mcp.json" and not (name.startswith("skills/zero-slop/") and name.endswith(".md")):
                self.assertEqual(files[name], original, name)
        self.assertEqual(set(files) - set(self.canonical), {
            "skills/zero-slop/scripts/" + name for name in build_plugin.MCP_RUNTIME})

    def test_all_runtime_instructions_and_reader_reference_route_to_mcp(self):
        files = self.overlay()
        for name, content in files.items():
            if name.startswith("skills/zero-slop/") and name.endswith(".md"):
                text = content.decode()
                self.assertIsNone(build_plugin._PYTHON_COMMAND.search(text), name)
                self.assertIsNone(build_plugin._INLINE_COMMAND.search(text), name)
                self.assertIsNone(build_plugin._UNROUTED_COMMAND.search(text), name)
        skill = files["skills/zero-slop/SKILL.md"].decode()
        for tool in ("version", "score", "portfolio", "heatmap", "register_delta", "rescue",
                     "predictability_probes", "predictability_score", "learn_reflect", "learn_voice"):
            self.assertIn(build_plugin.LOCAL_TOOL_PREFIX + tool, skill)
        reader = files["skills/zero-slop/references/reader-review.md"].decode()
        for tool in ("reader_prepare", "reader_skim", "reader_next", "reader_recall", "reader_report"):
            self.assertIn(build_plugin.LOCAL_TOOL_PREFIX + tool, reader)

    def test_source_editorial_algorithm_and_consent_survive(self):
        files = self.overlay()
        skill = files["skills/zero-slop/SKILL.md"].decode()
        source = self.canonical["skills/zero-slop/SKILL.md"].decode()
        headings = lambda text: re.findall(r"^#{1,6} .*$", text, re.M)
        self.assertEqual([heading for heading in headings(skill) if heading != "## Local tool routing"], headings(source))
        for phrase in ("Fidelity.", "Flag hollow spans", "No over-correction", "affirmative",
                       "separately before activating", "context isolation", "one targeted repair"):
            if phrase in source:
                self.assertIn(phrase, skill)
        self.assertEqual(skill.split("---", 2)[:2], source.split("---", 2)[:2])

    def test_new_helper_unknown_option_and_missing_mode_fail_closed(self):
        for command in ("python3 scripts/new_helper.py draft.md",
                        "python3 -B scripts/new_helper.py draft.md",
                        "`new_helper.py --unknown draft.md`",
                        "python3 scripts/slopscore.py --new-mode draft.md",
                        "python3 scripts/slopscore.py --fidelity --portfolio draft.md",
                        "python3 scripts/reader_review.py invented manifest.json"):
            files = dict(self.canonical)
            files["skills/zero-slop/SKILL.md"] += ("\n" + command + "\n").encode()
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.overlay(files=files)

    def test_check_wording_is_copy_only_and_keeps_requirement_and_citation(self):
        name = "skills/zero-slop/references/eval.md"
        source = self.canonical[name]
        text = self.overlay()[name].decode()
        self.assertIn("pass did not run", source.decode())
        self.assertNotIn("pass did not run", text)
        self.assertIn("check was not performed", text)
        self.assertIn("write the number down", text)
        self.assertIn("https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing", text)
        self.assertEqual(self.canonical[name], source)

    def test_inline_delta_heatmap_and_multiline_learning_route(self):
        source = "`python3 <skill-root>/scripts/register.py --delta <original> <final>`\n" \
                 "`python3 <skill-root>/scripts/slopscore.py --heatmap <file>`\n" \
                 "python3 scripts/learn.py --reflect --produced out.md \\\n  --shipped final.md --reason <reason>\n"
        routed = build_plugin._route_commands(source, self.rules["modules"], set(self.rules["required_tools"]))
        for tool in ("register_delta", "heatmap", "learn_reflect"):
            self.assertIn(build_plugin.LOCAL_TOOL_PREFIX + tool, routed)
        self.assertIn("--shipped final.md", routed)
        self.assertNotIn("python3", routed)

    def test_maintainer_provenance_does_not_invent_local_tools(self):
        text = build_plugin._route_commands("`register.py --recall`; `calibrate.py --decay`",
                                           self.rules["modules"], set(self.rules["required_tools"]))
        self.assertEqual(text.count("not an installed MCP operation"), 2)
        self.assertNotIn(build_plugin.LOCAL_TOOL_PREFIX, text)

    def test_missing_symlinked_templates_and_adapter_fail_without_writes(self):
        template = self.root / build_plugin.ANTHROPIC_OVERLAY / "routing.json"
        original = template.read_bytes()
        template.unlink()
        with self.assertRaises(ValueError):
            self.overlay()
        template.symlink_to(ROOT / build_plugin.ANTHROPIC_OVERLAY / "routing.json")
        with self.assertRaises(ValueError):
            self.overlay()
        template.unlink()
        template.write_bytes(original)
        (self.root / "scripts/mcp_stdio.py").unlink()
        with self.assertRaises(ValueError):
            self.overlay()
        self.assertFalse((self.root / "distribution/plugins").exists())

    def test_remote_config_drift_or_adapter_in_canonical_payload_is_rejected(self):
        for key, value in ((".mcp.json", b'{"mcpServers":{}}'),
                           ("skills/zero-slop/scripts/mcp_stdio.py", b"unexpected")):
            files = dict(self.canonical)
            files[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.overlay(files=files)

    def test_real_packaged_stdio_start_and_tools_list_from_arbitrary_cwd(self):
        files = self.overlay()
        folder = self.root / "installed plugin with spaces"
        for name, content in files.items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "offline-package-test", "version": "1"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", ZS_NO_UPDATE_CHECK="1",
                   ZERO_SLOP_NO_NOTES="1", ZERO_SLOP_HOME=str(self.root / "private-test-state"))
        result = subprocess.run([sys.executable, str(folder / "skills/zero-slop/scripts/mcp_stdio.py")],
                                input="\n".join(json.dumps(message) for message in messages) + "\n",
                                text=True, capture_output=True, cwd=self.root, env=env, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([response["id"] for response in responses], [1, 2])
        self.assertEqual(set(self.rules["required_tools"]),
                         {tool["name"] for tool in responses[1]["result"]["tools"]})
        self.assertFalse((self.root / "private-test-state").exists())


if __name__ == "__main__":
    unittest.main()
