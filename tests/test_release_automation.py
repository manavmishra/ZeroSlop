"""Fail-closed release identity and idempotent reconciliation contracts."""
import copy
import contextlib
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
from publication_guard import API, RAW, publication_guard  # noqa: E402
from registry_record import published_record  # noqa: E402
from reconcile_release import MCP, repair_plan  # noqa: E402
import npm_record  # noqa: E402


class PublicationGuard(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.tag = "v2.10.2"
        self.data = {
            f"{API}/compare/{self.sha}...main": {"status": "ahead"},
            f"{API}/actions/workflows/validate.yml/runs?event=push&branch=main&head_sha={self.sha}&per_page=10": {
                "workflow_runs": [{"id": 10, "head_sha": self.sha, "head_branch": "main", "event": "push", "run_number": 1}]},
            f"{API}/actions/runs/10/jobs?filter=latest&per_page=100": {
                "jobs": [{"name": name, "status": "completed", "conclusion": "success"} for name in ("validate", "website", "mcp")]},
            f"{RAW}/{self.sha}/package.json": {"name": "zero-slop", "version": "2.10.2"},
            f"{RAW}/main/package.json": {"name": "zero-slop", "version": "2.10.2"},
            f"{API}/git/ref/tags/{self.tag}": {"ref": f"refs/tags/{self.tag}", "object": {"type": "commit", "sha": self.sha}},
        }

    def check(self, **kwargs):
        return publication_guard(self.tag, self.sha, fetch_fn=self.data.__getitem__, **kwargs)

    def test_validated_tag_and_pre_tag_recovery(self):
        self.assertEqual(self.check()["version"], "2.10.2")
        del self.data[f"{API}/git/ref/tags/{self.tag}"]
        self.assertEqual(self.check(require_tag=False)["sha"], self.sha)

    def test_missing_failed_skipped_or_incomplete_validation_blocks(self):
        key = f"{API}/actions/runs/10/jobs?filter=latest&per_page=100"
        for bad in ([], [{"name": "validate", "status": "completed", "conclusion": "success"}],
                    [{"name": n, "status": "completed", "conclusion": "skipped"} for n in ("validate", "website", "mcp")]):
            with self.subTest(bad=bad):
                self.data[key] = {"jobs": bad}
                with self.assertRaises(ValueError): self.check()

    def test_newer_source_version_blocks_stale_publish(self):
        self.data[f"{RAW}/main/package.json"]["version"] = "2.10.3"
        with self.assertRaisesRegex(ValueError, "superseded"): self.check()

    def test_moved_tag_blocks_publish(self):
        self.data[f"{API}/git/ref/tags/{self.tag}"]["object"]["sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "immutable"): self.check()

    def test_untrusted_or_invalid_references_block(self):
        for tag in ("main", "v2.10.2-beta", "v2.10.2\nmain"):
            with self.assertRaises(ValueError): publication_guard(tag, self.sha, fetch_fn=self.data.__getitem__)
        self.data[f"{API}/compare/{self.sha}...main"]["status"] = "diverged"
        with self.assertRaisesRegex(ValueError, "trusted main"): self.check()

    def test_pull_request_run_is_not_release_authority(self):
        key = f"{API}/actions/workflows/validate.yml/runs?event=push&branch=main&head_sha={self.sha}&per_page=10"
        self.data[key]["workflow_runs"][0]["event"] = "pull_request"
        with self.assertRaisesRegex(ValueError, "trusted main validation"): self.check()


class RegistryRecord(unittest.TestCase):
    def test_existing_exact_record_skips_publish(self):
        server = {"name": "io.github.manavmishra/zero-slop", "version": "2.10.2", "remotes": [{"url": f"{MCP}/mcp", "type": "streamable-http"}]}
        data = {"server": server, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active"}}}
        self.assertTrue(published_record(server, fetch_fn=lambda _: data))
        drift = copy.deepcopy(data)
        drift["server"]["remotes"] = []
        with self.assertRaises(ValueError): published_record(server, fetch_fn=lambda _: drift)

    def test_only_explicit_404_is_unpublished(self):
        for status in (401, 404, 429, 503):
            def read(url): raise urllib.error.HTTPError(url, status, "test", {}, None)
            if status == 404:
                self.assertFalse(published_record({"version": "2.10.2"}, fetch_fn=read))
            else:
                with self.assertRaises(urllib.error.HTTPError): published_record({"version": "2.10.2"}, fetch_fn=read)


class NpmRecord(unittest.TestCase):
    def setUp(self):
        self.version, self.sha = "2.10.2", "a" * 40
        self.exact_url = f"{npm_record.NPM}/{self.version}"
        self.latest_url = f"{npm_record.NPM}/latest"
        self.data = {url: {"name": "zero-slop", "version": self.version, "gitHead": self.sha}
                     for url in (self.exact_url, self.latest_url)}
        self.requests = []

    def read(self, url):
        self.requests.append(url)
        result = self.data[url]
        if isinstance(result, Exception):
            raise result
        return result

    def check(self):
        return npm_record.publication_state(self.version, self.sha, fetch_fn=self.read)

    def test_noop_requires_both_exact_commit_and_latest(self):
        self.assertEqual(self.check(), {"status": "current", "version": self.version})
        self.assertEqual(self.requests, [self.exact_url, self.latest_url])

    def test_only_exact_version_404_means_unpublished(self):
        self.data[self.exact_url] = urllib.error.HTTPError(self.exact_url, 404, "Not Found", {}, None)
        self.assertEqual(self.check(), {"status": "unpublished", "version": self.version})
        self.assertEqual(self.requests, [self.exact_url])

    def test_http_and_transport_errors_block_on_either_lookup(self):
        for url in (self.exact_url, self.latest_url):
            errors = [urllib.error.HTTPError(url, status, "test", {}, None) for status in (401, 403, 429, 500, 503)]
            errors += [urllib.error.URLError("offline"), TimeoutError("timed out"), ValueError("bad JSON")]
            for error in errors:
                with self.subTest(url=url, error=error):
                    original = self.data[url]
                    self.data[url] = error
                    with self.assertRaises(type(error)):
                        self.check()
                    self.data[url] = original

    def test_empty_and_malformed_successful_exact_responses_are_not_missing(self):
        for record in ({}, [], None, "", {"error": "not found"}):
            with self.subTest(record=record):
                self.data[self.exact_url] = record
                with self.assertRaisesRegex(ValueError, "exists but does not match"):
                    self.check()

    def test_existing_exact_record_requires_name_version_and_full_git_head(self):
        valid = copy.deepcopy(self.data[self.exact_url])
        for key, value in (("name", "other"), ("version", "2.10.1"), ("gitHead", None),
                           ("gitHead", "a" * 7), ("gitHead", "b" * 40)):
            self.data[self.exact_url] = {**valid, key: value}
            with self.assertRaisesRegex(ValueError, "validated checkout SHA"):
                self.check()

    def test_stale_newer_or_missing_latest_requires_maintainer_auth(self):
        for latest in ({"name": "zero-slop", "version": "2.10.1"},
                       {"name": "zero-slop", "version": "2.10.3"},
                       urllib.error.HTTPError(self.latest_url, 404, "Not Found", {}, None)):
            self.data[self.latest_url] = latest
            with self.assertRaisesRegex(ValueError, "npm latest promotion requires maintainer auth"):
                self.check()

    def test_malformed_latest_is_blocked_without_advising_a_dist_tag_write(self):
        for latest in ({}, [], None, {"name": "other", "version": self.version},
                       {"name": "zero-slop", "version": None}):
            self.data[self.latest_url] = latest
            with self.assertRaisesRegex(ValueError, "latest metadata is invalid"):
                self.check()

    def test_latest_matching_version_with_wrong_commit_is_not_current(self):
        self.data[self.latest_url]["gitHead"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "latest does not match"):
            self.check()

    def test_invalid_inputs_never_reach_the_registry(self):
        for version, sha in (("2.10.2\nalready=true", self.sha), (None, self.sha),
                             (self.version, "main"), (self.version, self.sha + "\n")):
            with self.assertRaises(ValueError):
                npm_record.publication_state(version, sha, fetch_fn=self.read)
        self.assertEqual(self.requests, [])

    def test_cli_writes_only_fixed_outputs_after_success(self):
        for status, already in (("current", "true"), ("unpublished", "false")):
            output = io.StringIO()
            with mock.patch.object(npm_record, "publication_state", return_value={"status": status}), \
                    mock.patch.object(Path, "open", return_value=contextlib.nullcontext(output)), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(npm_record.main([
                    "--version", self.version, "--sha", self.sha,
                    "--github-output", "/tmp/synthetic-output-not-created",
                ]), 0)
            self.assertEqual(output.getvalue(), f"already={already}\nversion={self.version}\n")

    def test_cli_failure_cannot_emit_publication_outputs(self):
        with mock.patch.object(npm_record, "publication_state", side_effect=TimeoutError("offline")), \
                mock.patch.object(Path, "open") as opened, contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(npm_record.main([
                "--version", self.version, "--sha", self.sha,
                "--github-output", "/tmp/synthetic-output-not-created",
            ]), 1)
            opened.assert_not_called()
            self.assertIn("NPM_PUBLICATION_BLOCKED", error.getvalue())


class ReconcilePlan(unittest.TestCase):
    def setUp(self):
        self.version = "2.10.2"
        self.sha = "a" * 40
        self.data = {
            "https://registry.npmjs.org/zero-slop/latest": {"name": "zero-slop", "version": self.version, "gitHead": self.sha},
            f"https://registry.npmjs.org/zero-slop/{self.version}": {"name": "zero-slop", "version": self.version, "gitHead": self.sha},
            f"{API}/releases/latest": {"tag_name": "v2.10.2", "draft": False, "assets": [{"name": n, "state": "uploaded", "size": 100} for n in ("zero-slop.zip", "zero-slop-single-file.md", "Zero-Slop-One-Pager.pdf")]},
            f"{MCP}/health": {"ok": True, "editorConfigured": True, "version": self.version, "scorer": {"ok": True, "scorerVersion": self.version}},
            f"{MCP}/.well-known/mcp/server-card.json": {"serverInfo": {"version": self.version}},
            f"{MCP}/openapi.json": {"info": {"version": self.version}},
            "https://registry.modelcontextprotocol.io/v0.1/servers/io.github.manavmishra%2Fzero-slop/versions/latest": {
                "server": {"version": self.version}, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active", "isLatest": True}}},
        }

    def test_current_release_does_not_republish(self):
        self.assertEqual(repair_plan(self.version, self.sha, read=self.data.__getitem__), [])

    def test_api_drift_repairs_gateway_not_npm(self):
        self.data[f"{MCP}/openapi.json"]["info"]["version"] = "2.10.1"
        self.assertEqual(repair_plan(self.version, self.sha, read=self.data.__getitem__), [("deploy-mcp.yml", "main", ["-f", "release_tag=v2.10.2"])])

    def test_missing_assets_rebuild_release(self):
        self.data[f"{API}/releases/latest"]["assets"] = []
        self.assertEqual(repair_plan(self.version, self.sha, read=self.data.__getitem__), [("release-on-tag.yml", "v2.10.2", [])])

    def test_empty_or_partial_uploads_rebuild_release(self):
        for bad in ({"size": 0}, {"state": "starter"}):
            with self.subTest(bad=bad):
                data = copy.deepcopy(self.data)
                data[f"{API}/releases/latest"]["assets"][0].update(bad)
                self.assertEqual(repair_plan(self.version, self.sha, read=data.__getitem__), [("release-on-tag.yml", "v2.10.2", [])])

    def test_recognized_degraded_health_repairs_deployment(self):
        import io
        def read(url):
            if url.endswith("/health"):
                raise urllib.error.HTTPError(url, 503, "degraded", {}, io.BytesIO(json.dumps({
                    "service": "zero-slop-mcp", "ok": False, "version": self.version, "scorer": {"ok": False}
                }).encode()))
            return self.data[url]
        self.assertEqual(repair_plan(self.version, self.sha, read=read), [("deploy-mcp.yml", "main", ["-f", "release_tag=v2.10.2"])])

    def test_unpublished_npm_and_registry_drift_dispatch_exact_tag(self):
        self.data["https://registry.npmjs.org/zero-slop/latest"]["version"] = "2.10.1"
        self.data["https://registry.modelcontextprotocol.io/v0.1/servers/io.github.manavmishra%2Fzero-slop/versions/latest"]["server"]["version"] = "2.10.1"
        def read(url):
            if url == f"{npm_record.NPM}/{self.version}":
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
            return self.data[url]
        self.assertEqual(repair_plan(self.version, self.sha, read=read), [("publish-npm.yml", "v2.10.2", []), ("publish-mcp.yml", "v2.10.2", [])])

    def test_existing_version_with_stale_latest_blocks_repeated_noop_dispatch(self):
        self.data["https://registry.npmjs.org/zero-slop/latest"]["version"] = "2.10.1"
        with self.assertRaisesRegex(ValueError, "npm latest promotion requires maintainer auth"):
            repair_plan(self.version, self.sha, read=self.data.__getitem__)

    def test_existing_npm_version_from_another_commit_blocks_recovery(self):
        self.data[f"{npm_record.NPM}/{self.version}"]["gitHead"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "validated checkout SHA"):
            repair_plan(self.version, self.sha, read=self.data.__getitem__)

    def test_default_reader_preserves_exact_npm_404_instead_of_empty_json(self):
        def urlopen(request, timeout):
            self.assertEqual(timeout, 10)
            url = request.full_url
            if url == f"{npm_record.NPM}/{self.version}":
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
            self.assertIn(url, self.data)
            return io.BytesIO(json.dumps(self.data[url]).encode())
        # Exercise the real default fetch_json -> urlopen seam without network.
        with mock.patch("deploy_mcp.urllib.request.urlopen", side_effect=urlopen):
            self.assertEqual(repair_plan(self.version, self.sha), [("publish-npm.yml", "v2.10.2", [])])

    def test_service_errors_do_not_start_blind_redeployment(self):
        def unavailable(_): raise TimeoutError("service unavailable")
        with self.assertRaises(TimeoutError): repair_plan(self.version, self.sha, read=unavailable)

    def test_npm_only_publishes_after_validation(self):
        workflow = (ROOT / ".github/workflows/publish-npm.yml").read_text()
        self.assertNotIn("  push:", workflow)
        self.assertIn("publication_guard.py", workflow)
        self.assertIn(".github/scripts/npm_record.py", workflow)
        self.assertNotIn('if npm view "$name@$version"', workflow)
        self.assertNotIn("npm dist-tag", workflow)
        sync = (ROOT / ".github/workflows/sync-release.yml").read_text()
        self.assertIn('gh workflow run publish-npm.yml --ref "$TAG"', sync)
        self.assertIn("--before-tag", sync)


if __name__ == "__main__":
    unittest.main()
