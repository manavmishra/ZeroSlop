"""Offline acceptance checks for the clean marketplace payload and local ZIP."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_marketplace_package as package
import build_plugin


class MarketplacePackage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        # Copy precisely the canonical source set, plus manifests/docs/icons.
        for name in package.SUPPORT_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        for item in build_plugin.ITEMS:
            source = ROOT / item
            sources = build_plugin.wanted(source) if source.is_dir() else [source]
            for path in sources:
                target = self.root / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        for manifest_path in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            manifest = json.loads((ROOT / manifest_path).read_text())
            for section in (manifest, manifest.get("interface", {})):
                for key in package.ICON_KEYS:
                    if key in section:
                        relative = section[key].removeprefix("./")
                        target = self.root / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(ROOT / relative, target)

    def build(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return package.build(self.root, **kwargs)

    def test_exact_runtime_parity_and_minimal_support(self):
        self.assertEqual(self.build(), 0)
        folder = self.root / package.DEST
        files = {p.relative_to(folder).as_posix(): p.read_bytes()
                 for p in folder.rglob("*") if p.is_file()}
        expected = {}
        for item in build_plugin.ITEMS:
            source = ROOT / item
            sources = build_plugin.wanted(source) if source.is_dir() else [source]
            for path in sources:
                expected[f"skills/zero-slop/{path.relative_to(ROOT).as_posix()}"] = path.read_bytes()
        self.assertEqual({k: v for k, v in files.items() if k.startswith("skills/")}, expected)
        self.assertEqual(files, package.payload(self.root))
        allowed = set(package.SUPPORT_FILES)
        for manifest_name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            manifest = json.loads(files[manifest_name])
            for section in (manifest, manifest.get("interface", {})):
                allowed.update(section[key][2:] for key in package.ICON_KEYS
                               if key in section)
        self.assertEqual(set(files) - set(expected), allowed)

    def test_noncanonical_modes_fail_check_and_are_repaired(self):
        self.assertEqual(self.build(), 0)
        path = self.root / package.DEST / "skills/zero-slop/scripts/slopscore.py"
        path.chmod(0o755)
        self.assertEqual(self.build(check=True), 1)
        self.assertEqual(self.build(), 0)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o644)
        self.assertEqual(self.build(check=True), 0)

    def test_existing_openai_identity_only_changes_zip_manifest(self):
        name = "app-6a9df92463088191a02fffbdb21d7fe0"
        files = package.payload(self.root)
        original = files[".codex-plugin/plugin.json"]
        first = package.archive_bytes(files, name)
        self.assertEqual(first, package.archive_bytes(files, name))
        self.assertEqual(files[".codex-plugin/plugin.json"], original)
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            manifest = json.loads(archive.read(".codex-plugin/plugin.json"))
            self.assertEqual(manifest["name"], name)
            self.assertEqual(json.loads(archive.read(".claude-plugin/plugin.json"))["name"], "zero-slop")
            for entry in archive.infolist():
                self.assertEqual((entry.external_attr >> 16) & 0o777, 0o644)
        for invalid in ("../escape", "bad name", "A", "x" * 65):
            with self.assertRaises(ValueError):
                package.archive_bytes(files, invalid)

    def test_repository_only_material_is_absent(self):
        for name in ("website/page.html", "bin/zero-slop.mjs", "package-lock.json",
                     "plugin.json",
                     "bench/private.json", "assets/private.bin", "credentials.json",
                     "scripts/build_marketplace_package.py", "scripts/contextual.py",
                     "scripts/growth-snapshot.mjs"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("should never ship")
        self.assertEqual(self.build(), 0)
        files = package.payload(self.root)
        self.assertNotIn("plugin.json", files, "Codex metadata must not be overridden by an Agent Plugins root manifest")
        for name in files:
            self.assertNotIn("lock", name)
            self.assertNotIn("credentials", name)
            self.assertLessEqual(len(files[name]), package.MAX_BYTES)
        self.assertFalse(any((self.root / package.DEST).rglob("*.bin")))

    def test_check_is_read_only_and_detects_missing_changed_and_extra_files(self):
        self.assertEqual(self.build(check=True), 1)
        self.assertFalse((self.root / "distribution").exists())
        self.assertFalse((self.root / "tmp").exists())
        self.assertEqual(self.build(make_zip=True), 0)
        self.assertEqual(self.build(check=True, make_zip=True), 0)
        target = self.root / package.DEST / "LICENSE"
        target.write_text("changed")
        self.assertEqual(self.build(check=True), 1)
        self.assertEqual(target.read_text(), "changed")
        self.assertEqual(self.build(), 0)
        target.unlink()
        self.assertEqual(self.build(check=True), 1)
        self.assertEqual(self.build(), 0)
        extra = self.root / package.DEST / "unowned.txt"
        extra.write_text("preserve me")
        self.assertEqual(self.build(check=True), 1)
        self.assertEqual(self.build(), 1)
        self.assertEqual(extra.read_text(), "preserve me")

    def test_only_unchanged_owned_obsolete_files_are_removed(self):
        source = self.root / "references" / "retired.md"
        source.write_text("generated reference")
        self.assertEqual(self.build(), 0)
        target = self.root / package.DEST / "skills/zero-slop/references/retired.md"
        source.unlink()
        target.write_text("user changed this")
        self.assertEqual(self.build(), 1)
        self.assertTrue(target.exists())
        target.write_text("generated reference")
        self.assertEqual(self.build(), 0)
        self.assertFalse(target.exists())

    def test_unowned_empty_directories_are_preserved(self):
        self.assertEqual(self.build(), 0)
        directory = self.root / package.DEST / "unowned"
        directory.mkdir()
        self.assertEqual(self.build(), 1)
        self.assertEqual(self.build(check=True), 1)
        self.assertTrue(directory.is_dir())

    def test_source_and_destination_symlinks_are_refused_without_escaping_writes(self):
        with tempfile.TemporaryDirectory() as outside:
            outside = Path(outside)
            sentinel = outside / "sentinel"
            sentinel.write_text("preserve")
            link = self.root / "scripts" / "linked.py"
            link.symlink_to(sentinel)
            self.assertEqual(self.build(), 1)
            link.unlink()
            (self.root / "distribution").symlink_to(outside, target_is_directory=True)
            self.assertEqual(self.build(), 1)
            self.assertEqual(list(outside.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_text(), "preserve")

    def test_generated_file_and_zip_and_state_symlinks_are_refused(self):
        self.assertEqual(self.build(make_zip=True), 0)
        for relative in (package.DEST / "LICENSE", package.STATE, package.ZIP):
            with self.subTest(path=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.unlink()
                path.symlink_to(self.root / "LICENSE")
                self.assertEqual(self.build(make_zip=True), 1)
                path.unlink()
                path.write_bytes(original)

    def test_paths_cannot_escape_or_reference_credentials(self):
        for value in ("../outside", "/outside", "a/../../outside", "a\\b", "./a", "a//b"):
            with self.subTest(path=value), self.assertRaises(ValueError):
                package.safe_path(value)
        manifest_path = self.root / ".claude-plugin/plugin.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["icon"] = "./../outside.svg"
        manifest_path.write_text(json.dumps(manifest))
        self.assertEqual(self.build(), 1)

    def test_runtime_lockfiles_credentials_and_large_binaries_fail_closed(self):
        for name, content in (("scripts/package-lock.json", b"{}"),
                              ("data/credentials.json", b"{}"),
                              ("data/.env", b"credential"),
                              ("data/private.bin", b"binary"),
                              ("data/huge.json", b"x" * (package.MAX_BYTES + 1))):
            with self.subTest(path=name):
                path = self.root / name
                path.write_bytes(content)
                self.assertEqual(self.build(), 1)
                path.unlink()

    def test_mcp_credentials_are_rejected(self):
        config_path = self.root / ".mcp.json"
        config = json.loads(config_path.read_text())
        config["mcpServers"]["zero-slop"]["headers"] = {"Authorization": "fixture"}
        config_path.write_text(json.dumps(config))
        self.assertEqual(self.build(), 1)

    def test_zip_is_deterministic_and_has_codex_manifest_at_root(self):
        self.assertEqual(self.build(make_zip=True), 0)
        first = (self.root / package.ZIP).read_bytes()
        self.assertEqual(self.build(make_zip=True), 0)
        self.assertEqual((self.root / package.ZIP).read_bytes(), first)
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(set(archive.namelist()), set(package.payload(self.root)))
            self.assertIn(".codex-plugin/plugin.json", archive.namelist())
            manifest = json.loads(archive.read(".codex-plugin/plugin.json"))
            self.assertEqual(manifest["mcpServers"], "./.mcp.json")
            self.assertEqual(json.loads(archive.read(".mcp.json"))["mcpServers"],
                             {"zero-slop": {"type": "http", "url": package.MCP_URL}})
            for entry in archive.infolist():
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertTrue(stat.S_ISREG(entry.external_attr >> 16))
                self.assertEqual(archive.read(entry), package.payload(self.root)[entry.filename])
        (self.root / package.ZIP).write_bytes(b"stale")
        self.assertEqual(self.build(check=True, make_zip=True), 1)

    def test_packaged_scorer_imports_and_resolves_relative_data(self):
        self.assertEqual(self.build(), 0)
        scorer = self.root / package.DEST / "skills/zero-slop/scripts/slopscore.py"
        result = subprocess.run([sys.executable, str(scorer), "--json", "-"],
                                input="The cache expires after 15 minutes.", text=True,
                                capture_output=True, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ai_likelihood", json.loads(result.stdout))

    def test_claude_listing_fields_and_approved_square_logo(self):
        manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(manifest["icon"], "./.claude-plugin/icon.svg")
        expected = {"documentationUrl": "https://github.com/manavmishra/ZeroSlop#readme",
                    "supportUrl": "https://github.com/manavmishra/ZeroSlop/issues",
                    "privacyPolicyUrl": "https://zero-slop.ai/privacy/",
                    "termsOfServiceUrl": "https://zero-slop.ai/terms/"}
        for key, value in expected.items():
            self.assertEqual(manifest[key], value)
        icon = ROOT / ".claude-plugin/icon.svg"
        self.assertEqual(icon.read_bytes().strip(), (ROOT / "assets/logo/logo-mark.svg").read_bytes().strip())
        svg = ET.fromstring(icon.read_bytes())
        self.assertEqual(svg.attrib["width"], svg.attrib["height"])
        self.assertGreaterEqual(int(svg.attrib["width"]), 128)

    def test_maintainer_exclusions_match_npm(self):
        npm = json.loads((ROOT / "package.json").read_text())["files"]
        self.assertIn("build_marketplace_package.py", build_plugin.EXCLUDE)
        self.assertIn("growth-snapshot.mjs", build_plugin.EXCLUDE)
        for name in build_plugin.EXCLUDE:
            if name.endswith((".py", ".mjs")):
                self.assertIn(f"!scripts/{name}", npm)


if __name__ == "__main__":
    unittest.main()
