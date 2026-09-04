import assert from "node:assert/strict";
import test from "node:test";

import worker from "./index";
import { COUNTER_METRICS } from "./counter";

function signingKeyForTests(): string {
  return Array.from({ length: 40 }, (_, index) => String.fromCharCode(97 + (index % 26))).join("");
}

function healthEnv(scorerVersion: string): Env {
  return {
    SCORER_VERSION: "2.8.9",
    EDITOR_SHARED_SECRET: signingKeyForTests(),
    REPORT_SHARED_SECRET: signingKeyForTests(),
    SCORER: {
      fetch: async () => Response.json({ ok: true, scorerVersion }),
    },
  } as unknown as Env;
}

test("lifetime counters require the report-only bearer token", async () => {
  const env = healthEnv("2.8.9");
  env.MCP_COUNTER = {
    getByName(name: string) {
      return {
        async fetch() {
          return Response.json({
            schema: 1,
            startedAt: name === "global" ? "2026-09-03T20:00:00.000Z" : null,
            updatedAt: name === "global" ? "2026-09-03T20:01:00.000Z" : null,
            counters: Object.fromEntries(COUNTER_METRICS.map((metric) => [
              metric,
              name === "global" && metric === "mcp_tool_calls"
                ? 3
                : name === "global" && metric === "messages_deslopped"
                  ? 2
                  : 0,
            ])),
          });
        },
      };
    },
  } as unknown as Env["MCP_COUNTER"];

  const denied = await worker.fetch(
    new Request("https://mcp.zero-slop.ai/internal/counters"),
    env,
    {} as ExecutionContext,
  );
  assert.equal(denied.status, 401);

  const allowed = await worker.fetch(
    new Request("https://mcp.zero-slop.ai/internal/counters", {
      headers: { authorization: `Bearer ${signingKeyForTests()}` },
    }),
    env,
    {} as ExecutionContext,
  );
  assert.equal(allowed.status, 200);
  assert.equal(allowed.headers.get("cache-control"), "no-store");
  assert.deepEqual(await allowed.json(), {
    schema: 1,
    startedAt: "2026-09-03T20:00:00.000Z",
    updatedAt: "2026-09-03T20:01:00.000Z",
    counters: Object.fromEntries(COUNTER_METRICS.map((metric) => [
      metric,
      metric === "mcp_tool_calls" ? 3 : metric === "messages_deslopped" ? 2 : 0,
    ])),
  });
  assert.equal(denied.headers.get("www-authenticate"), 'Bearer realm="zero-slop-reports"');
});

test("health fails closed when the private scorer release drifts", async () => {
  const response = await worker.fetch(
    new Request("https://mcp.zero-slop.ai/health"),
    healthEnv("2.8.4"),
    {} as ExecutionContext,
  );

  assert.equal(response.status, 503);
  assert.equal((await response.json() as { ok: boolean }).ok, false);
  assert.equal(response.headers.get("cache-control"), "no-store");
});

test("health passes only for the exact scorer release", async () => {
  const response = await worker.fetch(
    new Request("https://mcp.zero-slop.ai/health"),
    healthEnv("2.8.9"),
    {} as ExecutionContext,
  );

  assert.equal(response.status, 200);
  assert.equal((await response.json() as { ok: boolean }).ok, true);
});

test("health fails closed when connector signing is not configured", async () => {
  const env = healthEnv("2.8.9");
  env.EDITOR_SHARED_SECRET = "";
  const response = await worker.fetch(
    new Request("https://mcp.zero-slop.ai/health"),
    env,
    {} as ExecutionContext,
  );

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), {
    ok: false,
    service: "zero-slop-mcp",
    version: "2.8.9",
    scorer: { ok: true, scorerVersion: "2.8.9" },
    editorConfigured: false,
  });
});

test("publishes a static server card for registry scanners", async () => {
  const response = await worker.fetch(
    new Request("https://mcp.zero-slop.ai/.well-known/mcp/server-card.json"),
    healthEnv("2.8.9"),
    {} as ExecutionContext,
  );
  const card = await response.json() as {
    serverInfo: { name: string; version: string };
    authentication: { required: boolean };
    tools: Array<{ name: string; inputSchema: { properties: { text: { maxLength: number } } } }>;
  };
  assert.equal(response.status, 200);
  assert.deepEqual(card.serverInfo, { name: "zero-slop", version: "2.8.9" });
  assert.equal(card.authentication.required, false);
  assert.equal(card.tools[0]?.name, "deslop");
  assert.equal(card.tools[0]?.inputSchema.properties.text.maxLength, 20_000);
});

test("rejects oversized MCP bodies before parsing or rate limiting", async () => {
  const env = healthEnv("2.8.9") as Env & { PIPELINE_LIMITER?: unknown };
  let limiterCalled = false;
  env.PIPELINE_LIMITER = {
    async limit() {
      limiterCalled = true;
      return { success: true };
    },
  };
  const body = JSON.stringify({
    jsonrpc: "2.0",
    method: "tools/call",
    params: { name: "deslop", arguments: { text: "x".repeat(140_000) } },
    id: 1,
  });
  const response = await worker.fetch(
    new Request("https://mcp.zero-slop.ai/mcp", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    }),
    env,
    {} as ExecutionContext,
  );

  assert.equal(response.status, 413);
  assert.equal(limiterCalled, false);
  assert.equal(response.headers.get("cache-control"), "no-store");
});

test("the request limit permits the full documented Unicode draft size", async () => {
  const body = JSON.stringify({
    jsonrpc: "2.0",
    method: "tools/call",
    params: { name: "deslop", arguments: { text: "🧭".repeat(20_000) } },
    id: 1,
  });
  const { requestBodyWithinLimit } = await import("./index");
  assert.equal(await requestBodyWithinLimit(new Request("https://mcp.zero-slop.ai/mcp", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  })), true);
});
