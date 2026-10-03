"""Offline acceptance for the static, MCP-only Anthropic package."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "distribution/plugins/zero-slop-hosted"
sys.path.insert(0, str(ROOT / "scripts"))
from check_release_version import is_release_path

FILES = frozenset({
    ".claude-plugin/plugin.json", ".claude-plugin/icon.svg", ".mcp.json",
    "README.md", "LICENSE",
})
MANIFEST_KEYS = frozenset({
    "$schema", "name", "displayName", "description", "version", "author",
    "homepage", "repository", "license", "icon", "documentationUrl",
    "supportUrl", "privacyPolicyUrl", "termsOfServiceUrl", "mcpServers",
})
MCP_URL = "https://mcp.zero-slop.ai/mcp"
MCP = {"mcpServers": {"zero-slop": {"type": "http", "url": MCP_URL}}}


def validate_package(folder: Path, version: str) -> None:
    """Reject extra/default components, unsafe paths, credentials and execution."""
    if any(path.is_symlink() for path in (folder, *folder.parents)):
        raise ValueError("symlink package root")
    entries = list(folder.rglob("*"))
    if {path.relative_to(folder).as_posix() for path in entries} != FILES | {".claude-plugin"}:
        raise ValueError("unexpected package entry")
    for path in entries:
        if path.is_symlink():
            raise ValueError("symlink package entry")
        if path.is_dir():
            continue
        if not path.is_file() or path.stat().st_size > 64 * 1024:
            raise ValueError("non-file or oversized package entry")
        if stat.S_IMODE(path.stat().st_mode) & 0o111:
            raise ValueError("executable package entry")
        path.read_text(encoding="utf-8")

    manifest = json.loads((folder / ".claude-plugin/plugin.json").read_text())
    if set(manifest) != MANIFEST_KEYS:
        raise ValueError("unexpected manifest component or setting")
    expected = {
        "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
        "name": "zero-slop-hosted", "displayName": "Zero Slop Hosted",
        "version": version, "license": "MIT",
        "icon": "./.claude-plugin/icon.svg", "mcpServers": "./.mcp.json",
        "author": {"name": "Manav Mishra", "url": "https://github.com/manavmishra"},
        "homepage": "https://zero-slop.ai/",
        "repository": "https://github.com/manavmishra/ZeroSlop",
        "documentationUrl": "https://github.com/manavmishra/ZeroSlop#readme",
        "supportUrl": "https://github.com/manavmishra/ZeroSlop/issues",
        "privacyPolicyUrl": "https://zero-slop.ai/privacy/",
        "termsOfServiceUrl": "https://zero-slop.ai/terms/",
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("incorrect identity, version, links or component paths")
    description = manifest.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("missing hosted description")
    if re.search(r"\b(run|install|execute|use|never|must|ignore|obey|follow)\b|\$\{|```", description, re.I):
        raise ValueError("execution or behavior instructions in description")
    if json.loads((folder / ".mcp.json").read_text()) != MCP:
        raise ValueError("unexpected server, credentials, environment or transport")

    readme = (folder / "README.md").read_text()
    if len(readme.split()) < 40:
        raise ValueError("README too short")
    for phrase in (
        MCP_URL, "server-side", "edited or unchanged", "writing heuristics",
        "not AI-authorship", "not a guarantee of factual accuracy",
        "Cloudflare Workers AI", "bounded", "OpenRouter fallback",
        "does not activate private learning", "separate", "retention policies",
        "https://zero-slop.ai/privacy/", "review candidate",
        "not evidence of publication or deployment", "https://mcp.zero-slop.ai/health",
    ):
        if phrase not in re.sub(r"\s+", " ", readme):
            raise ValueError(f"missing truthful README disclosure: {phrase}")
    if re.search(r"```|\$\{|\b(?:python3?|npx|npm|curl|bash|powershell)\b|\d+\.\d+\.\d+", readme, re.I):
        raise ValueError("README contains local execution or hardcoded deployment version")
    if (folder / "LICENSE").read_bytes() != (ROOT / "LICENSE").read_bytes():
        raise ValueError("license differs from canonical license")
    icon = folder / ".claude-plugin/icon.svg"
    if icon.read_bytes() != (ROOT / ".claude-plugin/icon.svg").read_bytes():
        raise ValueError("icon differs from approved mark")
    svg = ET.fromstring(icon.read_text())
    if int(svg.attrib["width"]) != int(svg.attrib["height"]) or int(svg.attrib["width"]) < 128:
        raise ValueError("icon is not square and at least128px")
    for element in svg.iter():
        if element.tag.rsplit("}", 1)[-1] in {"script", "foreignObject", "image", "use"}:
            raise ValueError("active or externally referenced SVG")
        if any(key.lower().startswith("on") or key.rsplit("}", 1)[-1] == "href" for key in element.attrib):
            raise ValueError("active SVG attribute")


class HostedPlugin(unittest.TestCase):
    def setUp(self):
        self.version = json.loads((ROOT / "package.json").read_text())["version"]

    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name).resolve() / "plugin"
        shutil.copytree(PACKAGE, folder)
        return folder

    def test_static_package_has_only_the_declared_anonymous_http_connector(self):
        validate_package(PACKAGE, self.version)

    def test_default_components_and_extra_files_are_rejected(self):
        for name in ("skills/a/SKILL.md", "scripts/a.py", "hooks/hooks.json",
                     "commands/a.md", "agents/a.md", "bin/a", "package.json",
                     ".app.json", "credentials.json", "large.bin", "empty-directory"):
            with self.subTest(name=name):
                folder = self.fixture()
                target = folder / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if name == "empty-directory":
                    target.mkdir()
                else:
                    target.write_text("unexpected")
                with self.assertRaises(ValueError):
                    validate_package(folder, self.version)

    def test_manifest_cannot_add_execution_or_credentials(self):
        for key in ("skills", "commands", "agents", "hooks", "settings", "userConfig",
                    "dependencies", "lspServers", "experimental", "workflows", "apps"):
            with self.subTest(key=key):
                folder = self.fixture()
                path = folder / ".claude-plugin/plugin.json"
                manifest = json.loads(path.read_text())
                manifest[key] = "./execute"
                path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    validate_package(folder, self.version)

    def test_mcp_rejects_commands_secrets_alternate_urls_and_servers(self):
        cases = (
            {"command": "node", "args": ["server.js"]},
            {"type": "http", "url": MCP_URL, "headers": {"Authorization": "Bearer dummy"}},
            {"type": "http", "url": MCP_URL, "env": {"API_KEY": "${API_KEY}"}},
            {"type": "http", "url": "https://example.com/mcp"},
            {"type": "stdio", "url": MCP_URL},
        )
        for server in cases:
            with self.subTest(server=server):
                folder = self.fixture()
                (folder / ".mcp.json").write_text(json.dumps({"mcpServers": {"zero-slop": server}}))
                with self.assertRaises(ValueError):
                    validate_package(folder, self.version)
        folder = self.fixture()
        (folder / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": MCP["mcpServers"]["zero-slop"]}}))
        with self.assertRaises(ValueError):
            validate_package(folder, self.version)

    def test_paths_cannot_escape_and_package_cannot_contain_symlinks(self):
        folder = self.fixture()
        path = folder / ".claude-plugin/plugin.json"
        manifest = json.loads(path.read_text())
        manifest["mcpServers"] = "../.mcp.json"
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            validate_package(folder, self.version)
        folder = self.fixture()
        icon = folder / ".claude-plugin/icon.svg"
        icon.unlink()
        icon.symlink_to(ROOT / ".claude-plugin/icon.svg")
        with self.assertRaises(ValueError):
            validate_package(folder, self.version)

    def test_executable_modes_and_oversized_allowed_files_are_rejected(self):
        folder = self.fixture()
        (folder / "README.md").chmod(0o755)
        with self.assertRaises(ValueError):
            validate_package(folder, self.version)
        folder = self.fixture()
        (folder / "README.md").write_text("x" * (64 * 1024 + 1))
        with self.assertRaises(ValueError):
            validate_package(folder, self.version)

    def test_deployed_version_and_published_status_are_not_assumed(self):
        for replace in (False, True):
            with self.subTest(replace=replace):
                folder = self.fixture()
                path = folder / "README.md"
                text = path.read_text()
                if replace:
                    text = text.replace("This directory is a review candidate, not evidence of publication or deployment.",
                                        "This plugin is published and live.")
                else:
                    text += "\nProduction is version2.12.13.\n"
                path.write_text(text)
                with self.assertRaises(ValueError):
                    validate_package(folder, self.version)

    def test_readme_examples_distinguish_rewrite_from_unedited_clear_text(self):
        text = re.sub(r"\s+", " ", (PACKAGE / "README.md").read_text())
        for draft in (
            "It is important to note that Maya reduced review time by 40% for Project Northstar. The team will decide on Friday.",
            "The meeting starts at 10 am on Friday.",
            "Version 3.2 fixes a crash on startup.",
        ):
            self.assertIn(draft, text)
        self.assertIn("Maya reduced review time by 40% for Project Northstar. The team will decide on Friday.", text)
        self.assertIn("Status: `rewritten`; writing scores: 41.7 to 9.5", text)
        self.assertIn("`modelRequests: 1`", text)
        self.assertEqual(text.count("status: `already_clear`; writing scores: 9.5 to 9.5"), 2)
        self.assertEqual(text.count("`factsPreserved: true`, `passedFinalChecks: false`, `modelRequests: 0`"), 2)
        self.assertIn("Editing did not run for the two already-clear examples", text)
        self.assertIn("not guaranteed edits or certification of Claude, mobile, or another MCP host", text)

    def test_hosted_payload_requires_version_maintenance_and_uses_existing_ci(self):
        manifest_path = "distribution/plugins/zero-slop-hosted/.claude-plugin/plugin.json"
        self.assertIn(f'"{manifest_path}"', (ROOT / "distribution/sync-version.mjs").read_text())
        for name in FILES:
            self.assertTrue(is_release_path(f"distribution/plugins/zero-slop-hosted/{name}"))
        workflow = (ROOT / ".github/workflows/validate.yml").read_text()
        self.assertIn("python3 scripts/check_distribution_manifests.py", workflow)
        self.assertIn("python3 -m unittest discover -s tests -p 'test_*.py'", workflow)
        self.assertIn("node distribution/sync-version.mjs --check", workflow)


if __name__ == "__main__":
    unittest.main()
