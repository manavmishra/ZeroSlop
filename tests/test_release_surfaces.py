"""Offline publication parity regressions; never fetch or execute package code."""
import base64
import contextlib
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import stat
import sys
import tarfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("release_surface_payloads", ROOT / "scripts/check_release_surfaces.py")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)
RELEASE = "https://api.github.com/repos/manavmishra/ZeroSlop/releases/latest"
ZIP = "https://github.com/manavmishra/ZeroSlop/releases/latest/download/zero-slop.zip"
NPM = "https://registry.npmjs.org/zero-slop/latest"
REGISTRY = "https://registry.modelcontextprotocol.io/v0.1/servers/io.github.manavmishra%2Fzero-slop/versions/latest"
DOWNLOAD = "https://zero-slop.ai/downloads/current-skill.zip?source=site&format=zip"
MANIFEST = "https://zero-slop.ai/try-runtime/manifest.json"


def make_zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def make_tar(files):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return output.getvalue()


def fixture_responses(module=CHECKER):
    """Full canonical bytes, shared with the older release-metadata tests."""
    version = json.loads((ROOT / "package.json").read_text())["version"]
    skill, npm = module.expected_payloads()
    tarball = make_tar({**{f"package/{k}": v for k, v in npm.items()},
                       "package/package.json": (ROOT / "package.json").read_bytes()})
    zip_blob = make_zip({f"zero-slop/{k}": v for k, v in skill.items()})
    tar_url = f"https://registry.npmjs.org/zero-slop/-/zero-slop-{version}.tgz"
    responses = {
        RELEASE: json.dumps({"tag_name": f"v{version}"}), ZIP: zip_blob, DOWNLOAD: zip_blob,
        NPM: json.dumps({"version": version, "dist": {
            "tarball": tar_url,
            "integrity": "sha512-" + base64.b64encode(hashlib.sha512(tarball).digest()).decode(),
        }}),
        tar_url: tarball,
        module.HOMEBREW: f'  url "{tar_url}"\n  sha256 "{hashlib.sha256(tarball).hexdigest()}"\n',
        REGISTRY: json.dumps({"server": {
            "name": "io.github.manavmishra/zero-slop", "version": version,
            "remotes": [{"type": "streamable-http", "url": f"{module.MCP}/mcp"}],
        }, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active", "isLatest": True}}}),
        f"{module.MCP}/health": json.dumps({
            "ok": True, "service": "zero-slop-mcp", "version": version,
            "scorer": {"ok": True, "scorerVersion": version}, "editorConfigured": True,
        }),
        f"{module.MCP}/.well-known/mcp/server-card.json": json.dumps({
            "serverInfo": {"name": "zero-slop", "version": version},
        }),
        f"{module.MCP}/openapi.json": json.dumps({
            "openapi": "3.1.2", "info": {"title": "Zero Slop API", "version": version},
            "servers": [{"url": module.MCP}],
            "paths": {"/v1/deslop": {"post": {"operationId": "deslop"}}},
        }),
        module.WEBSITE: '<a href="/downloads/current-skill.zip?source=site&amp;format=zip">Skill ZIP</a>',
        MANIFEST: json.dumps({"skillVersion": version, "files": {
            k: hashlib.sha256(skill[v]).hexdigest() for k, v in module.BROWSER_FILES.items()
        }}),
    }
    responses.update({f"{module.WEBSITE}try-runtime/zero-slop/{path}": skill[path]
                      for path in module.BROWSER_FILES.values()})
    return responses


class PayloadParity(unittest.TestCase):
    def setUp(self):
        self.responses = fixture_responses()
        self.requests = []

    def fetch(self, url, *, binary=False):
        self.requests.append((url, binary))
        key = url.split("?", 1)[0] if url.startswith(MANIFEST) else url
        self.assertIn(key, self.responses, f"unexpected fetch: {url}")
        result = self.responses[key]
        if isinstance(result, Exception):
            raise result
        return result

    def check(self, **kwargs):
        return CHECKER.check_once(fetch_fn=self.fetch, emit=lambda _: None, **kwargs)

    def test_complete_payloads_match_with_one_npm_download(self):
        self.assertEqual(self.check(), ([], []))
        tar_url = json.loads(self.responses[NPM])["dist"]["tarball"]
        self.assertEqual(self.requests.count((tar_url, True)), 1)
        self.assertIn((DOWNLOAD, True), self.requests)
        for path in CHECKER.BROWSER_FILES.values():
            self.assertIn((f"{CHECKER.WEBSITE}try-runtime/zero-slop/{path}", True), self.requests)

    def test_same_version_tampered_release_and_discovered_website_zip_fail(self):
        for url in (ZIP, DOWNLOAD):
            for change in ("changed", "missing", "unexpected"):
                with self.subTest(url=url, change=change):
                    original = self.responses[url]
                    files = CHECKER._zip_files(original)
                    path = "zero-slop/scripts/rescue.py"
                    if change == "changed":
                        files[path] += b"\n# synthetic drift\n"
                    elif change == "missing":
                        del files[path]
                    else:
                        files["zero-slop/scripts/unreviewed.py"] = b"synthetic"
                    self.responses[url] = make_zip(files)
                    problems, skipped = self.check()
                    self.responses[url] = original
                    self.assertEqual(skipped, [])
                    self.assertEqual(len(problems), 1, problems)
                    self.assertIn("runtime", problems[0])

    def test_npm_integrity_is_required_even_when_tarball_contents_are_valid(self):
        original = self.responses[NPM]
        for integrity in (None, "sha512-invalid", "sha256-unsupported"):
            metadata = json.loads(original)
            metadata["dist"]["integrity"] = integrity
            self.responses[NPM] = json.dumps(metadata)
            problems, skipped = self.check()
            self.assertEqual(skipped, [])
            self.assertEqual(len(problems), 1, problems)
            self.assertIn("dist.integrity", problems[0])

    def test_rehashed_npm_tampering_fails_canonical_runtime_comparison(self):
        for path in ("scripts/rescue.py", "bin/zero-slop.mjs", "plugin.json", "package.json"):
            with self.subTest(path=path):
                self.responses = fixture_responses()
                metadata = json.loads(self.responses[NPM])
                tar_url = metadata["dist"]["tarball"]
                files = CHECKER._tar_files(self.responses[tar_url])
                if path == "package.json":
                    package = json.loads(files["package/package.json"])
                    package["scripts"] = {"postinstall": "synthetic-do-not-execute"}
                    files["package/package.json"] = json.dumps(package).encode()
                else:
                    files[f"package/{path}"] += b"\nsynthetic drift\n"
                blob = make_tar(files)
                self.responses[tar_url] = blob
                metadata["dist"]["integrity"] = "sha512-" + base64.b64encode(hashlib.sha512(blob).digest()).decode()
                self.responses[NPM] = json.dumps(metadata)
                problems, skipped = self.check(skip_homebrew=True)
                self.assertEqual(skipped, [])
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(path, problems[0])

    def test_npm_metadata_cannot_redirect_to_an_unapproved_artifact(self):
        for url in ("http://registry.npmjs.org/zero-slop.tgz", "https://localhost/pkg.tgz",
                    "https://registry.npmjs.org/zero-slop/-/zero-slop-0.0.0.tgz"):
            metadata = json.loads(self.responses[NPM])
            metadata["dist"]["tarball"] = url
            self.responses[NPM] = json.dumps(metadata)
            problems, skipped = self.check()
            self.assertEqual(len(problems), 1, problems)
            self.assertEqual(skipped, [])
            self.assertNotIn((url, True), self.requests)

    def test_homebrew_version_and_exact_npm_checksum_are_independent_checks(self):
        original = self.responses[CHECKER.HOMEBREW]
        version = json.loads((ROOT / "package.json").read_text())["version"]
        for formula in (original.replace(version, "0.0.0"), original.replace('sha256 "', 'sha256 "0'),
                        original + 'version "0.0.0"\n', original + "version '0.0.0'\n", original + original,
                        original.replace(hashlib.sha256(next(v for k, v in self.responses.items()
                                                            if k.endswith(".tgz"))).hexdigest(), "a" * 64)):
            self.responses[CHECKER.HOMEBREW] = formula
            problems, skipped = self.check()
            self.assertEqual(skipped, [])
            self.assertEqual(len(problems), 1, problems)
            self.assertIn("Homebrew", problems[0])

    def test_skip_homebrew_is_explicit_and_does_not_skip_other_surfaces(self):
        self.responses[CHECKER.HOMEBREW] = "invalid formula"
        self.assertEqual(self.check(skip_homebrew=True), ([], []))
        self.assertNotIn((CHECKER.HOMEBREW, False), self.requests)
        self.assertIn((f"{CHECKER.MCP}/openapi.json", False), self.requests)
        self.assertIn((DOWNLOAD, True), self.requests)

    def test_rest_version_and_official_endpoint_are_required(self):
        url = f"{CHECKER.MCP}/openapi.json"
        original = json.loads(self.responses[url])
        for key, value in (("info", {"title": "Zero Slop API", "version": "0.0.0"}),
                           ("servers", [{"url": "http://mcp.zero-slop.ai"}]),
                           ("servers", [{"url": CHECKER.MCP}, {"url": "https://other.example"}]),
                           ("paths", {"/v1/deslop": {"get": {"operationId": "deslop"}}}),
                           ("paths", {})):
            self.responses[url] = json.dumps({**original, key: value})
            problems, skipped = self.check()
            self.assertEqual(skipped, [])
            self.assertEqual(len(problems), 1, problems)
            self.assertIn("REST OpenAPI", problems[0])

    def test_registry_must_advertise_exact_canonical_mcp_transport(self):
        original = json.loads(self.responses[REGISTRY])
        for remotes in (None, [], [{"type": "sse", "url": f"{CHECKER.MCP}/mcp"}],
                        [{"type": "streamable-http", "url": "https://unrelated.example/mcp"}]):
            data = copy.deepcopy(original)
            data["server"]["remotes"] = remotes
            self.responses[REGISTRY] = json.dumps(data)
            problems, skipped = self.check()
            self.assertEqual(skipped, [])
            self.assertEqual(len(problems), 1, problems)
            self.assertIn("MCP endpoint", problems[0])

    def test_browser_manifest_hashes_and_actual_file_bytes_both_must_match(self):
        original = self.responses[MANIFEST]
        manifest = json.loads(original)
        manifest["files"]["rescue"] = "a" * 64
        self.responses[MANIFEST] = json.dumps(manifest)
        problems, skipped = self.check()
        self.assertEqual(skipped, [])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("manifest hash differs", problems[0])
        self.responses[MANIFEST] = original
        url = f"{CHECKER.WEBSITE}try-runtime/zero-slop/scripts/rescue.py"
        self.responses[url] += b"\n# synthetic stale cached bytes\n"
        problems, skipped = self.check()
        self.assertEqual(skipped, [])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("served browser runtime bytes differ", problems[0])

    def test_missing_browser_hash_and_unknown_manifest_keys_never_control_fetches(self):
        manifest = json.loads(self.responses[MANIFEST])
        manifest["files"]["https://localhost/private"] = "a" * 64
        self.responses[MANIFEST] = json.dumps(manifest)
        self.assertEqual(self.check(), ([], []))
        self.assertFalse(any("localhost" in url for url, _ in self.requests))
        del manifest["files"]["rescue"]
        self.responses[MANIFEST] = json.dumps(manifest)
        self.assertEqual(len(self.check()[0]), 1)

    def test_new_network_failures_remain_optional_but_http_errors_are_drift(self):
        for url in (CHECKER.HOMEBREW, f"{CHECKER.MCP}/openapi.json",
                    f"{CHECKER.WEBSITE}try-runtime/zero-slop/scripts/rescue.py"):
            for offline in (True, False):
                with self.subTest(url=url, offline=offline):
                    original = self.responses[url]
                    self.responses[url] = (urllib.error.URLError("offline") if offline else
                                           urllib.error.HTTPError(url, 404, "Missing", {}, None))
                    problems, skipped = self.check()
                    self.responses[url] = original
                    self.assertEqual(len(problems), 0 if offline else 1, problems)
                    self.assertEqual(len(skipped), 1 if offline else 0, skipped)

    def test_cli_network_policy_and_skip_flags_are_preserved(self):
        for args, expected in (([], 0), (["--require-network"], 1)):
            with mock.patch.object(CHECKER, "check_once", return_value=([], ["offline"])) as checked, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(CHECKER.main([*args, "--skip-homebrew", "--skip-website"]), expected)
                checked.assert_called_once_with(skip_website=True, skip_homebrew=True)


class ArchiveSafety(unittest.TestCase):
    def test_zip_paths_duplicates_and_links_are_rejected(self):
        for name in ("../SKILL.md", "/SKILL.md", "zero-slop/../SKILL.md", "a\\SKILL.md", "a//SKILL.md"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                CHECKER._zip_files(make_zip({name: b"synthetic"}))
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            info = zipfile.ZipInfo("zero-slop/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, b"../../private")
        with self.assertRaisesRegex(ValueError, "non-regular"):
            CHECKER._zip_files(output.getvalue())
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("same/", b"")
            archive.writestr("same", b"duplicate normalized path")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            CHECKER._zip_files(output.getvalue())

    def test_tar_links_devices_duplicate_paths_and_traversal_are_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE):
            output = io.BytesIO()
            with tarfile.open(fileobj=output, mode="w:gz") as archive:
                info = tarfile.TarInfo("package/link")
                info.type = kind
                info.linkname = "../../private"
                archive.addfile(info)
            with self.assertRaisesRegex(ValueError, "non-regular"):
                CHECKER._tar_files(output.getvalue())
        with self.assertRaisesRegex(ValueError, "unsafe"):
            CHECKER._tar_files(make_tar({"../package/file": b"synthetic"}))
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for _ in range(2):
                archive.addfile(tarfile.TarInfo("package/duplicate"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            CHECKER._tar_files(output.getvalue())

    def test_member_total_and_member_count_limits_are_enforced(self):
        for reader, blob in ((CHECKER._zip_files, make_zip({"runtime": b"123456789"})),
                             (CHECKER._tar_files, make_tar({"runtime": b"123456789"}))):
            with mock.patch.object(CHECKER, "MAX_MEMBER_BYTES", 8), self.assertRaises(ValueError):
                reader(blob)
        with mock.patch.object(CHECKER, "MAX_UNPACKED_BYTES", 8), self.assertRaises(ValueError):
            CHECKER._zip_files(make_zip({"one": b"12345", "two": b"12345"}))
        with mock.patch.object(CHECKER, "MAX_UNPACKED_BYTES", 8), self.assertRaises(ValueError):
            CHECKER._tar_files(gzip.compress(b"x" * 9))
        for reader, writer in ((CHECKER._zip_files, make_zip), (CHECKER._tar_files, make_tar)):
            with mock.patch.object(CHECKER, "MAX_ARCHIVE_MEMBERS", 1), self.assertRaises(ValueError):
                reader(writer({"one": b"", "two": b""}))


if __name__ == "__main__":
    unittest.main()
