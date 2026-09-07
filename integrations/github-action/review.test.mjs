import assert from "node:assert/strict";
import test from "node:test";
import { command, markdownFiles, optionsFromEnvironment, reportSummary, reviewFiles, runtimeEnvironment } from "./review.mjs";

const base = "a".repeat(40);
const head = "b".repeat(40);
const env = { GITHUB_SHA: head, GITHUB_EVENT_NAME: "pull_request", GITHUB_REPOSITORY: "example/docs" };
const event = { pull_request: { base: { sha: base }, head: { sha: head, repo: { full_name: "example/docs" } } } };
const options = optionsFromEnvironment(env, event);

test("runtime isolates npm configs and omits inherited execution hooks", () => {
  const clean = runtimeEnvironment("/tmp/fixture", { PATH: "/usr/bin", NODE_OPTIONS: "--require=malicious", PYTHONPATH: "/untrusted", npm_config_registry: "https://untrusted.invalid" });
  assert.notEqual(clean.npm_config_userconfig, clean.npm_config_globalconfig);
  assert.equal(clean.npm_config_registry, "https://registry.npmjs.org/");
  assert.equal(clean.ZERO_SLOP_HOME, "/tmp/fixture/private");
  assert.equal(clean.NODE_OPTIONS, undefined);
  assert.equal(clean.PYTHONPATH, undefined);
});

test("offline defaults, exact SHAs, bounded options and privileged-event rejection", () => {
  assert.equal(options.mode, "score");
  assert.equal(options.threshold, null);
  assert.throws(() => optionsFromEnvironment({ ...env, "INPUT_BASE-SHA": "--exec=oops" }, event));
  assert.throws(() => optionsFromEnvironment({ ...env, "INPUT_MAX-FILES": "51" }, event));
  assert.throws(() => optionsFromEnvironment({ ...env, GITHUB_EVENT_NAME: "pull_request_target" }, event));
  assert.throws(() => optionsFromEnvironment({ ...env, INPUT_MODE: "deslop", GITHUB_REPOSITORY: "other/repo" }, event));
  assert.throws(() => optionsFromEnvironment({ ...env, INPUT_MODE: "deslop", "INPUT_FAIL-ABOVE": "25" }, event));
});

test("null-delimited filenames remain arguments, not shell syntax", () => {
  assert.deepEqual(markdownFiles("docs/a b.md\0docs/$(whoami).markdown\0x.js\0docs/a b.md\0"), ["docs/a b.md", "docs/$(whoami).markdown"]);
});

test("local scores are advisory; strict greater-than threshold; no source in report", async () => {
  let sent;
  const report = await reviewFiles({
    files: ["readme.md"], options: { ...options, threshold: 25 },
    readBlob: async () => ({ mode: "100644", size: 12, text: "Private words" }),
    runCli: async (args, text) => { sent = { args, text }; return { code: 0, stdout: JSON.stringify({ ai_likelihood: 25, hits: [{ text: "Private words" }] }) }; },
  });
  assert.deepEqual(sent.args, ["score", "-", "--", "--json", "--genre", "general"]);
  assert.equal(report.thresholdFailed, false);
  assert.equal(report.reviewed, 1);
  assert(!JSON.stringify(report).includes("Private words"));
  assert(!reportSummary(report).includes("Private words"));
});

test("large files, symlinks and excess files never reach the editor", async () => {
  let calls = 0;
  const report = await reviewFiles({
    files: ["link.md", "big.md", "extra.md"], options: { ...options, maxFiles: 2, mode: "deslop" },
    readBlob: async (file) => file === "link.md" ? { mode: "120000", size: 9, text: "../secret" } : { mode: "100644", size: 20_001, text: "x".repeat(20_001) },
    runCli: async () => { calls += 1; },
  });
  assert.equal(calls, 0);
  assert.equal(report.skipped, 3);
  let unicodeCalls = 0;
  const unicodeReport = await reviewFiles({
    files: ["within.md", "over.md"], options: { ...options, mode: "deslop" },
    readBlob: async (file) => ({ mode: "100644", size: file === "within.md" ? 80_000 : 80_004, text: "😀".repeat(file === "within.md" ? 20_000 : 20_001) }),
    runCli: async () => { unicodeCalls += 1; return { code: 0, stdout: JSON.stringify({ text: "fixture", status: "already_clear", before: { score: 9 }, after: { score: 9 } }) }; },
  });
  assert.equal(unicodeCalls, 1);
  assert.equal(unicodeReport.reviewed, 1);
  assert.equal(unicodeReport.skipped, 1);
});

test("score above threshold fails, and professional prose selects formal scoring", async () => {
  const report = await reviewFiles({
    files: ["a.md"], options: { ...options, genre: "professional", threshold: 25 },
    readBlob: async () => ({ mode: "100644", size: 10, text: "A factual note." }),
    runCli: async (args) => {
      assert.equal(args.at(-1), "--formal");
      return { code: 0, stdout: JSON.stringify({ ai_likelihood: 25.1 }) };
    },
  });
  assert.equal(report.thresholdFailed, true);
});

test("hosted result preserved in explicit report, but no text/note leaks to summary", async () => {
  const result = { text: "Returned private text", status: "rewritten_with_warnings", before: { score: 70 }, after: { score: 20 }, note: "private source span" };
  const report = await reviewFiles({
    files: ["a|<img src=x>.md"], options: { ...options, mode: "deslop" },
    readBlob: async () => ({ mode: "100644", size: 10, text: "draft text" }),
    runCli: async (args) => {
      assert.deepEqual(args, ["deslop", "-", "--genre", "general", "--json"]);
      return { code: 0, stdout: JSON.stringify(result) };
    },
  });
  assert.deepEqual(report.files[0].result, result);
  assert(!reportSummary(report).includes(result.text));
  assert(!reportSummary(report).includes("<img"));
  assert(!reportSummary(report).includes(result.note));
});

test("invalid and failed child responses count as failures without source disclosure", async () => {
  const report = await reviewFiles({
    files: ["a.md"], options,
    readBlob: async () => ({ mode: "100644", size: 3, text: "secret" }),
    runCli: async () => ({ code: 1, stdout: "secret" }),
  });
  assert.equal(report.errors, 1);
  assert(!JSON.stringify(report).includes("secret"));
});

test("child command is bounded and accepts draft on stdin", async () => {
  const result = await command(process.execPath, ["-e", "process.stdin.pipe(process.stdout)"], { input: "fixture" });
  assert.equal(result.stdout, "fixture");
  await assert.rejects(command(process.execPath, ["-e", "process.stdout.write('x'.repeat(1024))"], { maxBytes: 100 }), /size limit/);
  await assert.rejects(command(process.execPath, ["-e", "setTimeout(()=>{},10000)"], { timeoutMs: 20 }), /time limit/);
  await assert.rejects(command(process.execPath, ["-e", "process.stdout.write(Buffer.from([255]))"]), /valid UTF-8/);
});
