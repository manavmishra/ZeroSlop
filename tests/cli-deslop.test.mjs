import assert from "node:assert/strict";
import test from "node:test";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { deslop, DeslopError, GENRES, RESULT_STATUSES, isApprovedResult, validateInput, validateResult } from "../bin/lib/deslop.mjs";
import { mockFetch, result } from "./fixtures/mcp-transport.mjs";
import { withPath } from "./helpers/npm-command.mjs";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const entry = join(root, "bin/zero-slop.mjs");
// --import accepts a URL; a Windows drive-letter path is parsed as a protocol.
const preload = pathToFileURL(join(root, "tests/fixtures/mcp-transport.mjs")).href;
const source = "Maya will send the €24,800 budget by Friday.";

function run(args, { mode = "json", input = source, signal, waitFor = "tools/call", emptyPath = true } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ["--import", preload, entry, ...args], {
      cwd: root, env: { ...(emptyPath ? withPath(process.env, "") : process.env),
        ZERO_SLOP_TEST_TRANSPORT: mode, ZERO_SLOP_NO_NOTES: "1", PYTHONDONTWRITEBYTECODE: "1" },
      stdio: ["pipe", "pipe", "pipe", "ipc"],
    });
    let stdout = "";
    let stderr = "";
    const messages = [];
    let signalled = false;
    const timer = setTimeout(() => { child.kill("SIGKILL"); reject(new Error(`CLI test hung: ${args.join(" ")}`)); }, 8_000);
    child.stdout.setEncoding("utf8").on("data", (chunk) => { stdout += chunk; });
    child.stderr.setEncoding("utf8").on("data", (chunk) => { stderr += chunk; });
    child.on("message", (message) => {
      messages.push(message);
      if (signal && !signalled && (message.body?.method === waitFor || message.type === waitFor)) { signalled = true; child.kill(signal); }
    });
    child.on("error", (error) => { clearTimeout(timer); reject(error); });
    child.on("close", (code, terminated) => { clearTimeout(timer); resolve({ code, terminated, stdout, stderr, messages }); });
    child.stdin.on("error", () => {});
    if (input !== null) child.stdin.end(input);
  });
}

test("input normalization keeps only the MCP input and enforces all five genres", () => {
  for (const genre of GENRES) assert.deepEqual(validateInput({ text: `  ${source}\n`, genre, audience: " Readers ", filename: "private.md" }), { text: source, genre, audience: "Readers" });
  assert.deepEqual(validateInput({ text: source }), { text: source, genre: "general" });
  assert.equal(validateInput({ text: "x".repeat(20_000), audience: "a".repeat(200) }).text.length, 20_000);
  for (const input of [null, {}, { text: " " }, { text: "x".repeat(20_001) }, { text: "😀".repeat(20_001) },
    { text: source, genre: "formal" }, { text: source, genre: null }, { text: source, audience: 1 }, { text: source, audience: "a".repeat(201) }]) {
    assert.throws(() => validateInput(input), (error) => error instanceof DeslopError && error.code === "invalid_input");
  }
  assert.equal(Object.isFrozen(GENRES), true);
  assert.equal(Object.isFrozen(RESULT_STATUSES), true);
});

test("Unicode limits match MCP: 20,000 draft and 200 audience code points after trimming", () => {
  const text = "😀".repeat(20_000);
  const audience = "😀".repeat(200);
  assert.deepEqual(validateInput({ text: ` ${text}\n`, audience: ` ${audience}\n` }), { text, genre: "general", audience });
  assert.equal(text.length, 40_000);
  for (const input of [{ text: text + "a" }, { text: source, audience: audience + "a" }]) {
    assert.throws(() => validateInput(input), { code: "invalid_input" });
  }
  // A combining sequence still contains two code points, as in the MCP schema.
  assert.equal(validateInput({ text: "e\u0301".repeat(10_000) }).text.length, 20_000);
  assert.throws(() => validateInput({ text: "e\u0301".repeat(10_001) }), { code: "invalid_input" });
});

test("all 14 fields and all six statuses are preserved without reconstructing the result", async () => {
  const schemaSource = await readFile(join(root, "mcp/gateway/src/contract.ts"), "utf8");
  const schema = schemaSource.split("const deslopOutputSchema = z.object({")[1].split("\n});")[0];
  const keys = [...schema.matchAll(/^  (\w+):/gm)].map((match) => match[1]);
  assert.equal(keys.length, 14);
  for (const status of RESULT_STATUSES) {
    const value = result(status);
    assert.deepEqual(Object.keys(value), keys);
    assert.equal(validateResult(value), value);
    assert.ok(schema.includes(`"${status}"`));
  }
});

test("malformed structured fields cannot become a successful result", () => {
  const original = result();
  for (const key of Object.keys(original)) {
    const value = structuredClone(original);
    delete value[key];
    assert.throws(() => validateResult(value), { code: "invalid_response" }, key);
  }
  for (const mutate of [
    (value) => { value.after.score = NaN; }, (value) => { value.before.score = 101; },
    (value) => { value.modelRequests = 2; }, (value) => { value.durationMs = -1; },
    (value) => { value.after.register.findings = [{}]; }, (value) => { value.after.flags = [{}]; },
    (value) => { value.after.register.findings = [{ name: "x", rate: 0, budget: 0, found: 0.5, quote: "x" }]; },
    (value) => { value.after.shape.broetry = "false"; }, (value) => { value.status = "successful"; },
  ]) { const value = structuredClone(original); mutate(value); assert.throws(() => validateResult(value), { code: "invalid_response" }); }
});

test("bounded report strings use the same Unicode units as the MCP output schema", () => {
  const value = result();
  value.after.band = "😀".repeat(80);
  value.after.flags = [{ phrase: "😀".repeat(1_000), strength: 1, issue: "😀".repeat(2_000), direction: "😀".repeat(2_000) }];
  value.after.register.findings = [{ name: "😀".repeat(160), rate: 0, budget: 0, found: 0, quote: "😀".repeat(1_000) }];
  assert.equal(validateResult(value), value);
  value.after.band += "a";
  assert.throws(() => validateResult(value), { code: "invalid_response" });
});

test("approval requires preservation and correctly treats already_clear without model checks", () => {
  assert.equal(isApprovedResult(null), false);
  assert.equal(isApprovedResult({ status: "already_clear", factsPreserved: true, modelRequests: 0, scoreChange: 0 }), false);
  assert.equal(isApprovedResult(result()), true);
  assert.equal(result("already_clear").passedFinalChecks, false);
  assert.equal(isApprovedResult(result("already_clear")), true);
  for (const status of RESULT_STATUSES.filter((status) => !["rewritten", "already_clear"].includes(status))) assert.equal(isApprovedResult(result(status)), false);
  for (const value of [{ ...result(), factsPreserved: false }, { ...result(), passedFinalChecks: false },
    { ...result("already_clear"), modelRequests: 1 }, { ...result("already_clear"), scoreChange: -2 }]) assert.equal(isApprovedResult(value), false);
});

test("shared client initializes, negotiates a session, and calls exactly one tool", async (t) => {
  const requests = [];
  t.mock.method(globalThis, "fetch", mockFetch("session", requests));
  const value = await deslop({ text: source, genre: "email", audience: "Readers", privateProfile: "secret", path: "/private/draft.md" }, { clientName: "zero-slop-raycast", clientVersion: "2.10.0" });
  assert.deepEqual(value, result());
  assert.deepEqual(requests.map((item) => item.body.method), ["initialize", "notifications/initialized", "tools/call"]);
  assert.deepEqual(requests[2].body.params, { name: "deslop", arguments: { text: source, genre: "email", audience: "Readers" } });
  assert.deepEqual(requests[0].body.params.clientInfo, { name: "zero-slop-raycast", version: "2.10.0" });
  assert.equal(requests[2].headers["mcp-protocol-version"], "2025-06-18");
  assert.equal(requests[2].headers["mcp-session-id"], "safe-session-1");
  for (const request of requests) { assert.equal(request.redirect, "manual"); assert.equal(request.headers["cache-control"], "no-store"); }
  assert.ok(requests.every((request) => request.headers["user-agent"] === undefined), "Raycast is not counted as CLI");
});

test("CLI attribution adds only coarse application metadata to existing hosted requests", async (t) => {
  const requests = [];
  t.mock.method(globalThis, "fetch", mockFetch("json", requests));
  await deslop({ text: source }, { clientName: "zero-slop-cli", clientVersion: "2.10.1-private-build" });
  assert.deepEqual(requests.map((item) => item.body.method), ["initialize", "notifications/initialized", "tools/call"]);
  for (const request of requests) {
    assert.equal(request.headers["user-agent"], "zero-slop-cli/2");
    assert.doesNotMatch(JSON.stringify(request.headers), /private|machine|profile|filename/i);
  }
});

test("SSE handles split UTF-8, multiline data, notifications and unrelated IDs, then cancels the reader", async (t) => {
  const events = [];
  t.mock.method(globalThis, "fetch", mockFetch("sse", [], (event) => events.push(event)));
  assert.deepEqual(await deslop({ text: source }), result());
  assert.ok(events.some((event) => event.type === "body-cancelled"));
});

test("additive structured fields survive unchanged", async (t) => {
  t.mock.method(globalThis, "fetch", mockFetch("extra"));
  const value = await deslop({ text: source });
  assert.deepEqual(value.futureMetadata, { preserved: true });
  assert.equal(value.after.futureMetric, "kept");
});

for (const [mode, code] of [
  ["http429", "http_error"], ["redirect", "http_error"], ["rpc-error", "protocol_error"],
  ["tool-error", "tool_error"], ["missing-result", "invalid_response"], ["malformed-json", "invalid_response"],
  ["wrong-type", "invalid_response"], ["bad-report", "invalid_response"], ["wrong-id", "invalid_response"],
  ["unsupported", "unsupported_protocol"], ["network", "network_error"], ["large", "invalid_response"],
  ["bad-is-error", "invalid_response"],
  ["bad-session", "invalid_response"], ["bad-utf8", "invalid_response"], ["sse-truncated", "invalid_response"],
]) {
  test(`shared client rejects ${mode} without leaking server text or retrying`, async (t) => {
    const requests = [];
    t.mock.method(globalThis, "fetch", mockFetch(mode, requests));
    await assert.rejects(deslop({ text: source }), (error) => {
      assert.equal(error.code, code);
      assert.doesNotMatch(error.message, /PRIVATE SERVER TEXT/);
      if (mode === "http429") { assert.equal(error.httpStatus, 429); assert.equal(error.retryAfterSeconds, 10); }
      if (mode === "rpc-error") assert.equal(error.rpcCode, -32602);
      return true;
    });
    assert.ok(requests.filter((request) => request.body.method === "tools/call").length <= 1);
    assert.equal(requests.some((request) => request.url.includes("example.invalid")), false);
  });
}

test("invalid input, configuration and pre-cancelled requests make no network calls", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", () => { throw new Error("Network must not run"); });
  await assert.rejects(deslop({ text: "" }), { code: "invalid_input" });
  for (const options of [{ timeoutMs: NaN }, { timeoutMs: 0 }, { timeoutMs: 300_001 }, { clientName: "a@example.com" }]) await assert.rejects(deslop({ text: source }, options), { code: "invalid_input" });
  await assert.rejects(deslop({ text: source }, { signal: AbortSignal.abort() }), { code: "cancelled" });
  assert.equal(fetch.mock.callCount(), 0);
});

for (const mode of ["initialize-hang", "hang", "body-hang"]) {
  test(`timeout bounds ${mode}, with cancellation only for an outstanding tool`, async (t) => {
    const requests = [];
    t.mock.method(globalThis, "fetch", mockFetch(mode, requests));
    await assert.rejects(deslop({ text: source }, { timeoutMs: 25 }), { code: "timeout" });
    assert.equal(requests.filter((request) => request.body.method === "notifications/cancelled").length, mode === "initialize-hang" ? 0 : 1);
    assert.ok(requests.filter((request) => request.body.method === "tools/call").length <= 1);
  });
}

test("CLI remote JSON works without Python and preserves the full result", async () => {
  const value = await run(["deslop", "-", "--genre", "email", "--audience", "Readers", "--json"]);
  assert.equal(value.code, 0, value.stderr);
  assert.deepEqual(JSON.parse(value.stdout), result());
  assert.match(value.stderr, /sending this draft to mcp\.zero-slop\.ai/);
  assert.doesNotMatch(value.stderr, /Maya|24,800|Friday/);
  const request = value.messages.find((message) => message.body?.method === "tools/call");
  assert.deepEqual(request.body.params.arguments, { text: source, genre: "email", audience: "Readers" });
});

test("CLI accepts exact emoji boundaries and rejects only the next code point before upload", async () => {
  const text = "😀".repeat(20_000);
  const audience = "😀".repeat(200);
  const accepted = await run(["deslop", "-", "--audience", audience, "--json"], { input: text });
  assert.equal(accepted.code, 0, accepted.stderr);
  assert.deepEqual(accepted.messages.find((message) => message.body?.method === "tools/call").body.params.arguments, { text, genre: "general", audience });
  for (const [input, reader] of [[text + "a", audience], [text, audience + "a"]]) {
    const rejected = await run(["deslop", "-", "--audience", reader, "--json"], { input });
    assert.equal(rejected.code, 2, rejected.stderr);
    assert.equal(rejected.messages.length, 0);
    assert.equal(JSON.parse(rejected.stdout).error.code, "invalid_input");
  }
});

test("text stdout contains only the unchanged returned text; review is on stderr", async () => {
  const value = await run(["deslop", "-"], { mode: "sse" });
  assert.equal(value.code, 0, value.stderr);
  assert.equal(value.stdout, result().text);
  assert.match(value.stderr, /Status: rewritten/);
  assert.match(value.stderr, /70\.1 before, 9\.5 after/);
});

test("all six statuses remain available and approval-gated results are never erased", async () => {
  for (const status of RESULT_STATUSES) {
    const value = await run(["deslop", "-", "--json", "--require-approved"], { mode: `status:${status}` });
    assert.equal(value.code, ["already_clear", "rewritten"].includes(status) ? 0 : 3, value.stderr);
    assert.deepEqual(JSON.parse(value.stdout), result(status));
  }
  const warning = await run(["deslop", "-", "--json"], { mode: "status:rewritten_with_warnings" });
  assert.equal(warning.code, 0);
});

test("explicit files stay byte-identical; directories and multiple inputs never upload", async (t) => {
  const directory = await mkdtemp(join(tmpdir(), "zero-slop-cli-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const file = join(directory, "draft with spaces.md");
  await writeFile(file, source);
  const value = await run(["deslop", file, "--json"]);
  assert.equal(value.code, 0, value.stderr);
  assert.equal(await readFile(file, "utf8"), source);
  const args = value.messages.find((message) => message.body?.method === "tools/call").body.params.arguments;
  assert.equal(JSON.stringify(args).includes(directory), false);
  for (const files of [[directory], [file, file], [join(directory, "missing.md")]]) {
    const failed = await run(["deslop", ...files, "--json"]);
    assert.equal(failed.code, 2);
    assert.equal(failed.messages.length, 0);
    assert.ok(JSON.parse(failed.stdout).error);
  }
});

test("invalid CLI options, oversized and malformed UTF-8 input fail before network", async () => {
  for (const args of [[], ["-", "--genre", "invalid"], ["-", "--audience"], ["-", "--timeout", "Infinity"],
    ["-", "--timeout", "0"], ["-", "--json", "--json"], ["-", "--force"], ["-", "--endpoint", "https://example.invalid"],
    ["-", "--genre", "email", "--genre", "social"], ["-", "--audience", "a".repeat(201)]]) {
    const value = await run(["deslop", ...args]);
    assert.equal(value.code, 2, `${args}: ${value.stderr}`);
    assert.equal(value.messages.length, 0);
  }
  for (const input of [" ", "x".repeat(20_001), "x".repeat(128 * 1024 + 1), Buffer.from([0xff, 0xfe])]) {
    const value = await run(["deslop", "-", "--json"], { input });
    assert.equal(value.code, 2, value.stderr);
    assert.equal(value.messages.length, 0);
    assert.equal(JSON.parse(value.stdout).error.code, "invalid_input");
  }
});

test("CLI reports distinct failures and leaves JSON machine-readable", async () => {
  for (const [mode, expected] of [["http429", "http_error"], ["rpc-error", "protocol_error"], ["tool-error", "tool_error"], ["network", "network_error"]]) {
    const value = await run(["deslop", "-", "--json"], { mode });
    assert.equal(value.code, 1);
    assert.equal(JSON.parse(value.stdout).error.code, expected);
    assert.doesNotMatch(value.stdout + value.stderr, /PRIVATE SERVER TEXT/);
    if (mode === "http429") assert.match(value.stderr, /Retry-After: 10 seconds/);
  }
});

test("CLI timeout returns 124, keeps uncertainty explicit and never replays the tool", async () => {
  const value = await run(["deslop", "-", "--json", "--timeout", "0.05"], { mode: "hang" });
  assert.equal(value.code, 124, value.stderr);
  assert.equal(JSON.parse(value.stdout).error.code, "timeout");
  assert.match(value.stderr, /outcome is unknown/);
  assert.equal(value.messages.filter((message) => message.body?.method === "tools/call").length, 1);
});

test("CLI surfaces shared model limits without replaying the tool or leaking provider prose", async () => {
  for (const [mode, code, httpStatus] of [["usage-limit", "usage_limit", 429], ["budget-unavailable", "budget_unavailable", 503], ["bad-budget", "usage_limit", 429]]) {
    const value = await run(["deslop", "-", "--json"], { mode });
    assert.equal(value.code, 1);
    const error = JSON.parse(value.stdout).error;
    assert.equal(error.code, code);
    assert.equal(error.httpStatus, httpStatus);
    assert.equal(error.retryAfterSeconds, mode === "bad-budget" ? undefined : 86_400);
    assert.match(error.message, mode === "budget-unavailable" ? /Hosted capacity could not be checked/ : /temporarily busy or at its free usage limit/);
    assert.match(error.message, /Please (?:wait before trying again|try again later)/);
    assert.doesNotMatch(value.stdout + value.stderr, /PRIVATE SERVER TEXT/);
    assert.equal(value.messages.filter(message => message.body?.method === "tools/call").length, 1);
    if (mode !== "bad-budget") assert.match(value.stderr, /Retry-After: 86400 seconds\. No retry was sent/);
  }
});

for (const [signal, exit] of [["SIGINT", 130], ["SIGTERM", 143]]) {
  const signalOptions = { skip: process.platform === "win32" ? "Windows child.kill does not deliver POSIX signals; protocol cancellation and functional tests still run." : false };
  test(`CLI ${signal} returns ${exit} and requests best-effort cancellation`, signalOptions, async () => {
    const value = await run(["deslop", "-", "--json"], { mode: "hang", signal });
    assert.equal(value.code, exit, value.stderr);
    assert.equal(value.terminated, null);
    assert.equal(JSON.parse(value.stdout).error.code, "cancelled");
    assert.match(value.stderr, /hosted processing may still finish/);
    assert.equal(value.messages.filter((message) => message.body?.method === "tools/call").length, 1);
    assert.equal(value.messages.filter((message) => message.body?.method === "notifications/cancelled").length, 1);
  });
  test(`CLI ${signal} while reading stdin stops before any upload`, signalOptions, async () => {
    const value = await run(["deslop", "-", "--json"], { mode: "input-wait", signal, input: null, waitFor: "input-read" });
    assert.equal(value.code, exit, value.stderr);
    assert.equal(value.terminated, null);
    assert.equal(JSON.parse(value.stdout).error.code, "cancelled");
    assert.equal(value.messages.filter((message) => message.type === "request").length, 0);
    assert.doesNotMatch(value.stderr, /sending this draft/);
  });
}

test("version/help/local scoring never call the hosted service", async () => {
  for (const args of [["--version"], ["--help"], ["deslop", "--help"], ["where"]]) {
    const value = await run(args);
    assert.equal(value.code, 0, value.stderr);
    assert.equal(value.messages.length, 0);
  }
  const missingPython = await run(["score", "-", "--", "--json"]);
  assert.equal(missingPython.code, 127);
  assert.equal(missingPython.messages.length, 0);
  const score = await run(["score", "-", "--", "--json"], { emptyPath: false });
  assert.equal(score.code, 0, score.stderr);
  assert.equal(typeof JSON.parse(score.stdout).ai_likelihood, "number");
  assert.equal(score.messages.length, 0);
});
