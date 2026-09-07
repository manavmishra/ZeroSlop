// Clean-package acceptance check. No hosted calls unless explicitly given --live.
// Live mode sends only the two fixed synthetic drafts below, once each. Never
// accepts a user file, retries an edit, or publishes anything.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { access, mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolveNpmCommand, withPath } from "./helpers/npm-command.mjs";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const live = process.argv.includes("--live");
if (process.argv.slice(2).some((argument) => argument !== "--live")) {
  console.error("Usage: node tests/cli-package-e2e.mjs [--live]");
  process.exit(2);
}
const cases = [
  { name: "already-clear", text: "Maya owns the pricing review. The team will decide on Friday." },
  { name: "editorial-draft", text: "It is important to note that Maya owns the pricing review. The team will decide on Friday." },
];
const required = ["text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
  "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note"];
const directory = await mkdtemp(join(tmpdir(), "zero-slop-package-e2e-"));
const reportPath = join(directory, "report.json");
const report = { mode: live ? "clean package and live hosted MCP" : "clean package only; no hosted calls",
  nodeVersion: process.version, platform: process.platform, architecture: process.arch, directory, checks: [], hosted: [] };
const env = {
  PATH: process.env.PATH, SYSTEMROOT: process.env.SYSTEMROOT, SystemRoot: process.env.SystemRoot,
  WINDIR: process.env.WINDIR, HOME: directory, USERPROFILE: directory, TMPDIR: directory,
  npm_config_cache: join(directory, "npm-cache"), npm_config_userconfig: join(directory, "user.npmrc"),
  npm_config_globalconfig: join(directory, "global.npmrc"), npm_config_registry: "https://registry.npmjs.org/",
  ZERO_SLOP_HOME: join(directory, "private"), ZERO_SLOP_NO_NOTES: "1", ZS_NO_UPDATE_CHECK: "1", PYTHONDONTWRITEBYTECODE: "1",
};
for (const path of [env.npm_config_userconfig, env.npm_config_globalconfig]) await writeFile(path, "", { mode: 0o600 });
await mkdir(env.ZERO_SLOP_HOME);

function command(executable, args, options = {}) {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const child = spawn(executable, args, { cwd: options.cwd ?? directory, env: options.env ?? env, shell: false, stdio: ["pipe", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    let killTimer;
    const timeout = setTimeout(() => {
      child.kill("SIGTERM");
      killTimer = setTimeout(() => child.kill("SIGKILL"), 1_000);
    }, options.timeoutMs ?? 90_000);
    child.stdout.setEncoding("utf8").on("data", (chunk) => { stdout += chunk; });
    child.stderr.setEncoding("utf8").on("data", (chunk) => { stderr += chunk; });
    child.stdin.on("error", () => {});
    child.on("error", (error) => { clearTimeout(timeout); clearTimeout(killTimer); reject(error); });
    child.on("close", (code, signal) => {
      clearTimeout(timeout); clearTimeout(killTimer);
      resolve({ code, signal, stdout, stderr, elapsedMs: Date.now() - started });
    });
    child.stdin.end(options.input);
  });
}
async function record(name, action) {
  await action();
  report.checks.push({ name, passed: true });
  console.log(`${name}: passed`);
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, { mode: 0o600 });
}
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");

try {
  const pkg = JSON.parse(await readFile(join(root, "package.json"), "utf8"));
  report.packageVersion = pkg.version;
  assert.equal(pkg.engines?.node, undefined, "A package-wide Node engine restriction would also block the existing offline installer. Review compatibility before adding one.");
  const npm = await resolveNpmCommand();
  const packed = await command(npm.executable, [...npm.prefixArgs, "pack", "--offline", "--ignore-scripts", "--json", "--pack-destination", directory], { cwd: root });
  assert.equal(packed.code, 0, packed.stderr);
  const [manifest] = JSON.parse(packed.stdout);
  const tarball = join(directory, manifest.filename);
  report.tarball = { path: tarball, sha256: digest(await readFile(tarball)), integrity: manifest.integrity };
  const shipped = manifest.files.map((entry) => entry.path);
  for (const path of ["bin/zero-slop.mjs", "bin/lib/deslop.mjs", "bin/lib/deslop.d.mts", "scripts/slopscore.py", "data/patterns.json"]) assert.ok(shipped.includes(path), `${path} missing from tarball`);
  assert.equal(shipped.some((path) => path.startsWith("tests/") || path.startsWith("integrations/")), false);
  const prefix = join(directory, "install");
  const installed = await command(npm.executable, [...npm.prefixArgs, "install", "--offline", "--prefix", prefix, "--ignore-scripts", "--no-audit", "--no-fund", tarball]);
  assert.equal(installed.code, 0, installed.stderr);
  const packageRoot = join(prefix, "node_modules", "zero-slop");
  const bin = process.platform === "win32" ? join(packageRoot, "bin", "zero-slop.mjs") : join(prefix, "node_modules", ".bin", "zero-slop");
  await access(bin);
  if (process.platform === "win32") await access(join(prefix, "node_modules", ".bin", "zero-slop.cmd"));
  for (const path of ["bin/zero-slop.mjs", "bin/lib/deslop.mjs", "bin/lib/deslop.d.mts"]) {
    const source = await readFile(join(root, path));
    // npm's bin linker normalizes only a CRLF shebang, even on Windows.
    // Keep the rest of the installed source byte-for-byte checked.
    const expected = path === "bin/zero-slop.mjs"
      ? Buffer.from(source.toString("utf8").replace(/^(#![^\r\n]*)\r\n/, "$1\n"))
      : source;
    assert.deepEqual(await readFile(join(packageRoot, path)), expected, `${path} changed during installation`);
  }
  const { validateResult, isApprovedResult } = await import(pathToFileURL(join(packageRoot, "bin/lib/deslop.mjs")).href);
  await record("pack and clean offline install", async () => {});
  const cli = (args, options) => command(process.execPath, [bin, ...args], options);

  await record("installed bin version and help", async () => {
    const version = await cli(["--version"]);
    assert.equal(version.code, 0, version.stderr);
    assert.equal(version.stdout.trim(), pkg.version);
    for (const args of [["--help"], ["deslop", "--help"]]) {
      const help = await cli(args);
      assert.equal(help.code, 0, help.stderr);
      assert.match(help.stdout, /deslop <file\|->/);
      assert.match(help.stdout, /Unicode code points/);
    }
  });
  await record("legacy Cursor and Codex install commands use only the isolated temporary home", async () => {
    for (const harness of ["cursor", "codex"]) {
      const expected = join(directory, `.${harness}`, "skills", "zero-slop");
      const location = await cli(["where", "--harness", harness]);
      assert.equal(location.code, 0, location.stderr);
      assert.equal(location.stdout.trim(), expected);
      const installation = await cli(["install", "--harness", harness]);
      assert.equal(installation.code, 0, installation.stderr);
      assert.deepEqual(await readFile(join(expected, "SKILL.md")), await readFile(join(packageRoot, "SKILL.md")));
      const repeated = await cli(["install", "--harness", harness]);
      assert.equal(repeated.code, 1, "Existing installation must not be overwritten without --force");
      const update = await cli(["install", "--harness", harness, "--force"]);
      assert.equal(update.code, 0, update.stderr);
      assert.deepEqual(await readFile(join(expected, "scripts", "slopscore.py")), await readFile(join(packageRoot, "scripts", "slopscore.py")));
    }
  });
  const draft = join(directory, "synthetic-clear.md");
  await writeFile(draft, cases[0].text, { mode: 0o600 });
  const originalHash = digest(await readFile(draft));
  await record("offline score file and stdin; source unchanged", async () => {
    for (const args of [["score", draft, "--", "--json"], ["score", "-", "--", "--json"]]) {
      const score = await cli(args, { input: cases[0].text });
      assert.equal(score.code, 0, score.stderr);
      assert.equal(typeof JSON.parse(score.stdout).ai_likelihood, "number");
      assert.doesNotMatch(score.stderr, /Hosted editing:/);
    }
    assert.equal(digest(await readFile(draft)), originalHash);
  });
  await record("missing Python affects score, not CLI setup", async () => {
    const noPython = withPath(env, "");
    const score = await cli(["score", "-", "--", "--json"], { env: noPython, input: cases[0].text });
    assert.equal(score.code, 127, score.stderr);
    const version = await cli(["--version"], { env: noPython });
    assert.equal(version.code, 0, version.stderr);
  });

  if (live) {
    console.log("Live mode: sending two fixed synthetic drafts to mcp.zero-slop.ai, once each; no retry.");
    for (const [index, sample] of cases.entries()) {
      const args = ["deslop", index === 0 ? draft : "-", "--genre", "professional", "--json", "--require-approved", "--timeout", "75"];
      const outcome = await cli(args, { input: sample.text, env: withPath(env, "") });
      const json = JSON.parse(outcome.stdout);
      const summary = { case: sample.name, exitCode: outcome.code, signal: outcome.signal, elapsedMs: outcome.elapsedMs,
        ...(json.error ? { error: json.error } : { status: json.status, scorerVersion: json.scorerVersion,
          before: json.before?.score, after: json.after?.score, modelRequests: json.modelRequests,
          passedFinalChecks: json.passedFinalChecks, factsPreserved: json.factsPreserved,
          serverDurationMs: json.durationMs, resultFields: Object.keys(json) }) };
      report.hosted.push(summary);
      await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, { mode: 0o600 });
      assert.ok(outcome.code === 0 || outcome.code === 3, `Live CLI failed: ${JSON.stringify(summary)}`);
      validateResult(json);
      for (const field of required) assert.ok(Object.hasOwn(json, field), `${field} missing from live result`);
      assert.equal(outcome.code, isApprovedResult(json) ? 0 : 3);
      assert.match(outcome.stderr, /Hosted editing: sending this draft/);
      assert.equal(digest(await readFile(draft)), originalHash);
      if (index === 0) {
        assert.equal(json.status, "already_clear", "The fixed clear sample unexpectedly needed editing");
        assert.equal(json.modelRequests, 0);
        assert.equal(json.text, sample.text);
      }
      await record(`live ${sample.name}, no Python, full result and approval gate`, async () => {});
    }
    assert.ok(report.hosted.reduce((sum, item) => sum + item.modelRequests, 0) <= 2);
  }
  report.passed = true;
} catch (error) {
  report.passed = false;
  report.failure = error instanceof Error ? error.message : "Acceptance check failed";
  process.exitCode = 1;
} finally {
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, { mode: 0o600 });
  console.log(JSON.stringify({ ...report, reportPath }, null, 2));
}
