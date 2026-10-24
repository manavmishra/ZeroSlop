import assert from "node:assert/strict";
import test from "node:test";

import worker from "./index";

// The Worker runs on the Workers Free plan, which stops an invocation after
// 10 ms of CPU time. workerd freezes timers between I/O, so CPU is measured
// here in Node with process.cpuUsage() around the whole request, including
// reading the response body. The budget is well under the plan limit so that
// slower CI hosts and production variance keep headroom.
const CPU_BUDGET_MS = 5;
const WARMUP_RUNS = 25;
const MEASURED_RUNS = 60;
const BODY_DEADLINE_MS = 1000;

// Node's fetch Request drops the forbidden Host header that workerd keeps.
// Restore it so the SDK's Host validation sees what production sees.
const nativeHeadersGet = Headers.prototype.get;
Headers.prototype.get = function get(this: Headers, name: string) {
  const value = nativeHeadersGet.call(this, name);
  return value === null && name.toLowerCase() === "host" ? "mcp.zero-slop.ai" : value;
};

// The scorer is a separate Worker reached over a service binding. The stub
// reports every draft as already clear, so a deslop call runs the gateway's
// own validation, scoring round trip and result shaping without a model call.
const cleanReport = {
  score: 5, band: "clear", words: 7, sentences: 1, flaggedPhrases: 0, sentenceVariety: "natural", readability: "clear",
  highWeightFlags: 0, punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
  shape: { measured: true, broetry: false, oneSentenceParagraphShare: 0, longestFragmentRun: 0 },
  register: { measured: true, words: 7, checked: 1, findings: [], twoPartContrasts: 0, announcements: 0 }, flags: [],
};

const env = {
  SCORER_VERSION: "2.12.1",
  ALLOWED_ORIGINS: "https://zero-slop.ai,https://www.zero-slop.ai,https://chatgpt.com,https://claude.ai",
  EDITOR_SHARED_SECRET: "x".repeat(40),
  REPORT_SHARED_SECRET: "x".repeat(40),
  PIPELINE_LIMITER: { limit: async () => ({ success: true }) },
  MCP_COUNTER: { getByName: () => ({ fetch: async () => Response.json({}) }) },
  SCORER: { fetch: async () => Response.json(cleanReport) },
} as unknown as Env;
const ctx = { waitUntil() {}, passThroughOnException() {} } as unknown as ExecutionContext;

const MODERN = "2026-07-28";
const modernMeta = {
  "io.modelcontextprotocol/protocolVersion": MODERN,
  "io.modelcontextprotocol/clientInfo": { name: "claude-code", version: "2.1.0" },
  "io.modelcontextprotocol/clientCapabilities": {},
};

type Probe = { name: string; request: () => Request; expect?: string };

function legacy(method: string, params?: Record<string, unknown>): () => Request {
  const body = JSON.stringify({ jsonrpc: "2.0", id: 1, method, ...(params ? { params } : {}) });
  return () => new Request("https://mcp.zero-slop.ai/mcp", {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json, text/event-stream" },
    body,
  });
}

function modern(method: string, id: string | number, params: Record<string, unknown> = {}): () => Request {
  const body = JSON.stringify({ jsonrpc: "2.0", id, method, params: { _meta: modernMeta, ...params } });
  return () => new Request("https://mcp.zero-slop.ai/mcp", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json, text/event-stream",
      "mcp-method": method,
      "mcp-protocol-version": MODERN,
    },
    body,
  });
}

const probes: Probe[] = [
  { name: "2025-era initialize", request: legacy("initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "claude-code", version: "2.1.0" } }) },
  { name: "2025-era tools/list", request: legacy("tools/list") },
  { name: "2026-era server/discover", request: modern("server/discover", "discover-1") },
  { name: "2026-era tools/list", request: modern("tools/list", 1) },
  { name: "2026-era subscriptions/listen", request: modern("subscriptions/listen", "listen:0", { notifications: { toolsListChanged: true } }) },
  {
    name: "2025-era tools/call deslop",
    request: legacy("tools/call", { name: "deslop", arguments: { text: "The importer now maps CSV headers automatically." } }),
    expect: '"status":"already_clear"',
  },
  {
    // The largest draft the contract accepts: 20,000 four-byte characters,
    // about 80 KiB of the 128 KiB body limit.
    name: "2025-era tools/call deslop, maximum draft",
    request: legacy("tools/call", { name: "deslop", arguments: { text: "🧭".repeat(20_000) } }),
    expect: '"status":"already_clear"',
  },
  { name: "server card", request: () => new Request("https://mcp.zero-slop.ai/.well-known/mcp/server-card.json") },
];

async function drain(response: Response): Promise<string> {
  if (!response.body) return "";
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let text = "";
  const deadline = Date.now() + BODY_DEADLINE_MS;
  try {
    while (true) {
      let timer: ReturnType<typeof setTimeout> | undefined;
      const chunk = await Promise.race([
        reader.read(),
        new Promise<never>((_, reject) => {
          timer = setTimeout(() => reject(new Error(`response body still open after ${BODY_DEADLINE_MS} ms`)), Math.max(0, deadline - Date.now()));
        }),
      ]).finally(() => clearTimeout(timer));
      if (chunk.done) return text + decoder.decode();
      text += decoder.decode(chunk.value, { stream: true });
    }
  } finally {
    void reader.cancel().catch(() => undefined);
  }
}

async function cpuMs(probe: Probe): Promise<number> {
  const request = probe.request();
  const started = process.cpuUsage();
  const response = await worker.fetch(request, env, ctx);
  const body = await drain(response);
  const used = process.cpuUsage(started);
  assert.ok(response.status < 400, `${probe.name} answered ${response.status}`);
  if (probe.expect) assert.ok(body.includes(probe.expect), `${probe.name} did not return ${probe.expect}: ${body.slice(0, 200)}`);
  return (used.user + used.system) / 1000;
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)]!;
}

for (const probe of probes) {
  test(`${probe.name} stays under ${CPU_BUDGET_MS} ms of CPU`, async () => {
    for (let run = 0; run < WARMUP_RUNS; run += 1) await cpuMs(probe);
    const samples: number[] = [];
    for (let run = 0; run < MEASURED_RUNS; run += 1) samples.push(await cpuMs(probe));
    const observed = median(samples);
    console.log(`cpu ${probe.name}: median ${observed.toFixed(2)} ms over ${MEASURED_RUNS} runs`);
    assert.ok(observed <= CPU_BUDGET_MS, `${probe.name} used a median ${observed.toFixed(2)} ms of CPU; the budget is ${CPU_BUDGET_MS} ms`);
  });
}

test("an MCP POST body is read once, never cloned", async () => {
  const nativeClone = Request.prototype.clone;
  let clones = 0;
  Request.prototype.clone = function clone(this: Request) {
    clones += 1;
    return nativeClone.call(this);
  } as typeof nativeClone;
  try {
    for (const probe of probes.filter(({ name }) => name.includes("-era"))) {
      clones = 0;
      await drain(await worker.fetch(probe.request(), env, ctx));
      assert.equal(clones, 0, `${probe.name} cloned the request ${clones} times`);
    }
  } finally {
    Request.prototype.clone = nativeClone;
  }
});
