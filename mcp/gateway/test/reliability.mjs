#!/usr/bin/env node
// Actual TCP/HTTP into local workerd. No Wrangler config, credentials, remote
// bindings, real scorer/model, or outbound network access is loaded.
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import http from "node:http";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { build } from "esbuild";
import { Miniflare, Log, LogLevel, convertV4MiniflareOptions } from "miniflare";

const directory = fileURLToPath(new URL(".", import.meta.url));
const pages = resolve(process.env.ZERO_SLOP_TEST_PAGES_ROOT ?? resolve(directory, "../../../ZSWebpage"));
const source = "It is important to note that Maya owns the report. Omar will read it by Friday.";
const clean = "Maya owns the report. Omar will read it by Friday.";
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const bundle = await build({ entryPoints: [resolve(directory, "reliability-worker.ts")], bundle: true,
  write: false, format: "esm", platform: "neutral", target: "es2024", conditions: ["workerd", "worker", "browser"],
  external: ["cloudflare:*", "node:*"], plugins: [{ name: "local-pages", setup(builder) {
    builder.onResolve({ filter: /^reliability:pages-editor$/ }, () => ({ path: resolve(pages, "functions/api/demo-rewrite.js") }));
  } }] });
const options = convertV4MiniflareOptions({ name: "reliability", modules: true, script: bundle.outputFiles[0].text,
  compatibilityDate: "2026-09-03", compatibilityFlags: ["nodejs_compat", "enable_request_signal"],
  unsafeDirectSockets: [{ host: "127.0.0.1", port: 0 }],
  outboundService: { name: "reliability", entrypoint: "Editor" },
  durableObjects: { MCP_COUNTER: { className: "ReliabilityBudget", useSQLite: true } },
  bindings: { EDITOR_SHARED_SECRET: randomBytes(32).toString("hex"), EDITOR_ENDPOINT: "https://editor.invalid/api/demo-rewrite",
    SCORER_VERSION: "synthetic-local", ALLOWED_ORIGINS: "https://zero-slop.ai", EDITOR_DAILY_NEURONS: "8000" },
  log: new Log(LogLevel.ERROR),
});
options.telemetry = { enabled: false };
options.unsafeInspectDurableObjects = true;
options.handleStructuredLogs = () => {};
const mf = new Miniflare(options);
const results = [];
const disconnectOnly = process.argv.includes("--disconnect-only");
let base;
function send(path, body, { disconnect = false, client = 1, method = "POST", incomplete = false } = {}) {
  const bytes = body === undefined ? undefined : JSON.stringify(body);
  let req;
  const started = performance.now();
  const done = new Promise((resolve, reject) => {
    req = http.request(new URL(path, base), { method, agent: false, headers: {
      host: "mcp.zero-slop.ai", "content-type": "application/json", accept: "application/json, text/event-stream",
      "cf-connecting-ip": `192.0.2.${client}`, ...(bytes ? { "content-length": Buffer.byteLength(bytes) } : {}),
    } }, (response) => {
      let text = "";
      response.setEncoding("utf8"); response.on("data", (chunk) => { text += chunk; });
      response.on("end", () => resolve({ status: response.statusCode, headers: response.headers, text, ms: performance.now() - started }));
      response.on("error", (error) => disconnect ? resolve({ disconnected: true, ms: performance.now() - started }) : reject(error));
    });
    req.on("error", (error) => disconnect ? resolve({ disconnected: true, ms: performance.now() - started }) : reject(error));
    req.setTimeout(45000, () => req.destroy(new Error("local_test_socket_timeout")));
    if (incomplete) req.write("{"); else req.end(bytes);
  });
  return { done, destroy: (mode = "reset") => mode === "reset" && req.socket ? req.socket.resetAndDestroy() : req.destroy() };
}
const control = async (phase, extra = {}) => { assert.equal((await send("/__control", { phase, ...extra }).done).status, 200); };
const stats = async (phase) => JSON.parse((await send(`/__stats?phase=${phase}`, undefined, { method: "GET" }).done).text);
async function until(phase, predicate, timeout = 4000) {
  const start = performance.now();
  while (performance.now() - start < timeout) {
    const value = await stats(phase);
    if (predicate(value)) return value;
    await sleep(15);
  }
  throw new Error(`local fixture did not reach expected state: ${phase}: ${JSON.stringify(await stats(phase))}`);
}
function percentiles(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const p = (q) => Math.round(sorted[Math.max(0, Math.ceil(q * sorted.length) - 1)] * 100) / 100;
  return { p50Ms: p(.5), p95Ms: p(.95), p99Ms: p(.99), maxMs: p(1) };
}
async function record(phase, assertions) {
  const value = await stats(phase);
  assert.equal(value.outboundBlocked, 0);
  assert.ok(value.reservedNeurons <= 8000);
  assert.ok(value.modelStarts <= value.grants);
  results.push({ phase, ...assertions, counters: value });
  process.stderr.write(`PASS ${phase}\n`);
}
try {
  base = await mf.unsafeGetDirectURL("reliability");
  if (!disconnectOnly) {
  await control("paced-soak");
  const durations = []; const soakStarted = performance.now();
  // 10 requests/sec for 60 seconds, one ordinary scorer request each; model
  // budget is reserved only for dirty text, not multiplied by transport.
  for (let i = 0; i < 600; i++) {
    await sleep(Math.max(0, soakStarted + i * 100 - performance.now()));
    const response = await send("/v1/deslop", { text: clean }).done;
    assert.equal(response.status, 200); assert.equal(JSON.parse(response.text).modelRequests, 0);
    durations.push(response.ms);
  }
  const soak = await stats("paced-soak");
  assert.equal(soak.scorerCalls, 600); assert.equal(soak.modelStarts, 0); assert.equal(soak.active, 0);
  await record("paced-soak", { requests: 600, elapsedMs: Math.round(performance.now() - soakStarted), ...percentiles(durations) });

  await control("concurrent-budget");
  const burst = await Promise.all(Array.from({ length: 48 }, (_, i) => send("/v1/deslop", { text: source }, { client: i + 1 }).done));
  const b = await stats("concurrent-budget");
  assert.equal(b.reserveAttempts, 48); assert.equal(b.modelStarts, b.grants);
  assert.equal(burst.filter((r) => r.status === 200).length, b.grants);
  assert.ok(b.grants > 0 && b.grants < 48);
  for (const response of burst.filter((r) => r.status !== 200)) {
    assert.equal(response.status, 429); assert.equal(JSON.parse(response.text).code, "usage_limit");
    assert.ok(Number(response.headers["retry-after"]) > 0);
  }
  const storage = await mf.unsafeGetDurableObjectStorage("reliability", "ReliabilityBudget", { name: "concurrent-budget/editor-budget-v1" });
  assert.equal((await storage.exec("SELECT reserved FROM editor_budget_days"))[0].reserved, b.reservedNeurons);
  await mf.unsafeEvictDurableObject("reliability", "ReliabilityBudget", { name: "concurrent-budget/editor-budget-v1" });
  const afterEviction = await send("/v1/deslop", { text: source }, { client: 100 }).done;
  assert.equal(afterEviction.status, 429);
  await record("concurrent-budget", { requests: 49, ...percentiles(burst.map((r) => r.ms)), sqliteReservationMatches: true, survivesEviction: true });

  await control("same-client-burst");
  const same = await Promise.all(Array.from({ length: 16 }, () => send("/v1/deslop", { text: source }).done));
  assert.equal(same.filter((r) => r.status === 200).length, 2);
  assert.equal((await stats("same-client-burst")).modelStarts, 2);
  await record("same-client-burst", { requests: 16 });

  for (const [phase, fault, expectedStarts, expectedCode] of [
    ["missing-gate", { missingBudget: true }, 0, "budget_unavailable"],
    ["failed-gate", { reserveFailure: true }, 0, "budget_unavailable"],
    ["malformed-gate", { reserveMalformed: true }, 0, "budget_unavailable"],
    ["late-gate", { reserveDelay: 2300 }, 0, "budget_unavailable"],
    ["failed-scorer", { scorerFailure: true }, 0, "service_unavailable"],
    ["malformed-scorer", { scorerMalformed: true }, 0, "service_unavailable"],
    ["stalled-scorer", { scorerDelay: 8500 }, 0, "service_unavailable"],
  ]) {
    await control(phase, fault);
    const response = await send("/v1/deslop", { text: source }).done;
    assert.equal(response.status, 503); assert.equal(JSON.parse(response.text).code, expectedCode);
    assert.ok(response.ms < (phase === "stalled-scorer" ? 9000 : 3000));
    await until(phase, (s) => !s.reservePending && !s.scorerPending);
    assert.equal((await stats(phase)).modelStarts, expectedStarts);
    await record(phase, { responseMs: Math.round(response.ms) });
  }
  for (const [phase, fault] of [["failed-model", { modelFailure: true }], ["stalled-model", { modelDelay: 24500 }]]) {
    await control(phase, fault);
    const response = await send("/v1/deslop", { text: source }).done;
    assert.equal(response.status, 200); assert.equal(JSON.parse(response.text).passedFinalChecks, false);
    assert.ok(response.ms < 26000);
    await until(phase, (s) => !s.modelPending);
    const s = await stats(phase); assert.equal(s.modelStarts, 1); assert.equal(s.grants, 1);
    await record(phase, { responseMs: Math.round(response.ms), fallbackOnly: true });
  }

  await control("whole-pipeline-deadline", { scorerDelay: 7000, modelDelay: 23500 });
  const deadlineResponse = await send("/v1/deslop", { text: source }).done;
  assert.equal(deadlineResponse.status, 503);
  assert.ok(deadlineResponse.ms >= 35000 && deadlineResponse.ms < 38000);
  await until("whole-pipeline-deadline", (s) => !s.scorerPending && !s.modelPending);
  assert.equal((await stats("whole-pipeline-deadline")).modelStarts, 1);
  await record("whole-pipeline-deadline", { responseMs: Math.round(deadlineResponse.ms), sharedDeadline: true });

  await control("slow-mcp-body");
  const slow = send("/mcp", undefined, { incomplete: true });
  const slowResponse = await slow.done;
  assert.equal(slowResponse.status, 408); assert.equal(JSON.parse(slowResponse.text).error, "body_timeout");
  assert.ok(slowResponse.ms >= 9900 && slowResponse.ms < 12000);
  assert.equal((await stats("slow-mcp-body")).scorerCalls, 0);
  await record("slow-mcp-body", { responseMs: Math.round(slowResponse.ms) });
  slow.destroy();
  }

  for (const [phase, path, fault, reached, starts] of [
    ["rest-disconnect-before-gate", "/v1/deslop", { scorerDelay: 500 }, (s) => s.scorerPending === 1, 0],
    ["rest-disconnect-reservation", "/v1/deslop", { reserveDelay: 500 }, (s) => s.reservePending === 1, 0],
    ["rest-disconnect-inference", "/v1/deslop", { modelDelay: 500 }, (s) => s.modelPending === 1, 1],
    ["web-disconnect-reservation", "/api/demo-rewrite", { reserveDelay: 500 }, (s) => s.reservePending === 1, 0],
    ["web-disconnect-inference", "/api/demo-rewrite", { modelDelay: 500 }, (s) => s.modelPending === 1, 1],
    ["mcp-disconnect-before-gate", "/mcp", { scorerDelay: 500 }, (s) => s.scorerPending === 1, 0],
    ["mcp-disconnect-reservation", "/mcp", { reserveDelay: 500 }, (s) => s.reservePending === 1, 0],
    ["mcp-disconnect-inference", "/mcp", { modelDelay: 500 }, (s) => s.modelPending === 1, 1],
  ]) {
    await control(phase, fault);
    const body = path === "/mcp" ? { jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "deslop", arguments: { text: source } } } : { text: source };
    const socket = send(path, body, { disconnect: true });
    await until(phase, reached);
    const cancelled = performance.now(); socket.destroy(); await socket.done;
    const observed = await until(phase, (s) => s.aborts === 1 && s.active === 0 && s.results.length === 1, 2000);
    const settledMs = Math.round(performance.now() - cancelled);
    assert.ok(settledMs < 1000, `${phase} cancellation must settle promptly`);
    await until(phase, (s) => !s.scorerPending && !s.reservePending && !s.modelPending);
    const s = await stats(phase); assert.equal(s.modelStarts, starts);
    if (phase.includes("reservation")) assert.equal(s.grants, 1, "uncertain/late grants are not refunded");
    if (phase.includes("inference")) assert.equal(s.modelAborts, 1, "cancellation reaches fake AI even when it ignores the signal");
    assert.equal(observed.completed, 1);
    await record(phase, { socketDisconnected: true, tcpMode: "RST", settledMs });
  }

  // A FIN after a fully uploaded HTTP/1 request is not necessarily a canceled
  // request to the server. Measure this separately; never fake an AbortSignal.
  await control("tcp-fin-observation", { scorerDelay: 100, modelDelay: 200 });
  const fin = send("/v1/deslop", { text: source }, { disconnect: true });
  await until("tcp-fin-observation", (s) => s.scorerPending === 1);
  const finStarted = performance.now(); fin.destroy("fin"); await fin.done;
  const finResult = await until("tcp-fin-observation", (s) => s.active === 0 && !s.modelPending);
  assert.ok(finResult.modelStarts <= 1);
  await record("tcp-fin-observation", { tcpMode: "FIN", abortObserved: finResult.aborts > 0,
    settledMs: Math.round(performance.now() - finStarted), providerStopGuaranteed: false });
  process.stdout.write(JSON.stringify({ localOnly: true, productionSLA: false, modelInferenceCalls: 0,
    scope: disconnectOnly ? "disconnect-only" : "full",
    runtime: "local workerd via Miniflare direct TCP socket", results,
    limitations: ["Synthetic upstreams; not real model latency, quality, account billing or regional capacity.",
      "Local workerd does not emulate all edge limits, network hops, proxy disconnect handling or production durability.",
      "Abort bounds caller waiting; a provider ignoring it may keep computing. Reservations are retained.",
      "A fully uploaded HTTP/1 request followed by TCP FIN may not trigger Request.signal; TCP RST tests do. Edge/browser proxy behavior is not certified.",
      "Short paced soak and bounded bursts are regression evidence, not enterprise SLA or long-duration load certification."] }, null, 2) + "\n");
} finally { await mf.dispose(); }
