import assert from "node:assert/strict";
import test from "node:test";

import {
  COUNTER_METRICS,
  COUNTER_SHARD_COUNT,
  countMcpRequest,
  countPipelineResult,
  isCounterSnapshot,
  readCounterSnapshot,
  reportTokenMatches,
} from "./counter";
import type { McpRequestMeta } from "./telemetry";
import type { PipelineResult } from "./types";

function meta(method: string): McpRequestMeta {
  return {
    method,
    tool: method === "tools/call" ? "deslop" : "none",
    client: "codex",
    clientVersion: "1",
    protocolVersion: "2025-06-18",
    country: "US",
    colo: "LAX",
    origin: "none",
    isDeslopCall: method === "tools/call",
  };
}

function counterEnv(recorded: string[][], names: string[] = []): Env {
  return {
    MCP_COUNTER: {
      getByName(name: string) {
        names.push(name);
        return {
          async fetch(_input: RequestInfo | URL, init?: RequestInit) {
            const body = JSON.parse(String(init?.body)) as { eventId: string; metrics: string[] };
            assert.match(body.eventId, /^[0-9a-f-]{36}$/);
            recorded.push(body.metrics);
            return new Response(null, { status: 204 });
          },
        };
      },
    },
  } as unknown as Env;
}

test("counts successful initializations separately from MCP tool calls", async () => {
  const recorded: string[][] = [];
  const env = counterEnv(recorded);
  await countMcpRequest(env, meta("initialize"), 200);
  await countMcpRequest(env, meta("tools/call"), 200);
  await countMcpRequest(env, meta("tools/call"), 500);
  assert.deepEqual(recorded, [
    ["client_initializations"],
    ["mcp_tool_calls"],
    ["mcp_tool_calls", "request_errors"],
  ]);
});

test("counts only changed outputs as messages deslopped", async () => {
  const recorded: string[][] = [];
  const env = counterEnv(recorded);
  const base = { factsPreserved: true, passedFinalChecks: false } as PipelineResult;

  await countPipelineResult(env, { ...base, status: "rewritten_with_warnings" });
  await countPipelineResult(env, { ...base, status: "already_clear" });
  await countPipelineResult(env, { ...base, status: "unchanged_verification_failed" });

  assert.deepEqual(recorded, [
    ["deslop_results", "safe_responses", "messages_deslopped", "review_warnings"],
    ["deslop_results", "safe_responses", "already_clear"],
    ["deslop_results", "safe_responses", "unchanged_responses"],
  ]);
});

test("writes are distributed across bounded counter shards", async () => {
  const recorded: string[][] = [];
  const names: string[] = [];
  await countMcpRequest(counterEnv(recorded, names), meta("tools/call"), 200);
  assert.equal(names.length, 1);
  assert.match(names[0] ?? "", /^shard-\d{2}$/);
  assert.ok(Number(names[0]?.slice(-2)) < COUNTER_SHARD_COUNT);
});

test("counter writes retry transient service failures", async () => {
  let attempts = 0;
  const eventIds: string[] = [];
  const env = {
    MCP_COUNTER: {
      getByName() {
        return {
          async fetch(_input: RequestInfo | URL, init?: RequestInit) {
            attempts += 1;
            eventIds.push(JSON.parse(String(init?.body)).eventId);
            return new Response(null, { status: attempts === 1 ? 503 : 204 });
          },
        };
      },
    },
  } as unknown as Env;

  await countMcpRequest(env, meta("tools/call"), 200);
  assert.equal(attempts, 2);
  assert.equal(new Set(eventIds).size, 1, "a retry must reuse its idempotency key");
});

function snapshot(count: number, startedAt: string | null, updatedAt: string | null) {
  return {
    schema: 1 as const,
    startedAt,
    updatedAt,
    counters: Object.fromEntries(COUNTER_METRICS.map((metric) => [metric, count])),
  };
}

test("lifetime reads aggregate legacy data and every current shard", async () => {
  const names: string[] = [];
  const env = {
    MCP_COUNTER: {
      getByName(name: string) {
        names.push(name);
        return {
          async fetch() {
            if (name === "global") {
              return Response.json(snapshot(2, "2026-09-01T00:00:00.000Z", "2026-09-01T00:01:00.000Z"));
            }
            if (name === "shard-00") {
              return Response.json(snapshot(3, "2026-09-02T00:00:00.000Z", "2026-09-03T00:00:00.000Z"));
            }
            return Response.json(snapshot(0, null, null));
          },
        };
      },
    },
  } as unknown as Env;

  const result = await readCounterSnapshot(env);
  assert.equal(names.length, COUNTER_SHARD_COUNT + 1);
  assert.equal(names[0], "global");
  assert.equal(result.counters.mcp_tool_calls, 5);
  assert.equal(result.counters.messages_deslopped, 5);
  assert.equal(result.startedAt, "2026-09-01T00:00:00.000Z");
  assert.equal(result.updatedAt, "2026-09-03T00:00:00.000Z");
});

test("counter snapshots reject partial, impossible, and unsafe payloads", () => {
  assert.equal(isCounterSnapshot(snapshot(0, null, null)), true);
  assert.equal(isCounterSnapshot({ schema: 1, startedAt: null, updatedAt: null, counters: {} }), false);
  assert.equal(isCounterSnapshot(snapshot(-1, null, null)), false);
  assert.equal(isCounterSnapshot(snapshot(0, "not-a-date", "2026-09-03T00:00:00.000Z")), false);
  assert.equal(isCounterSnapshot(snapshot(0, "2026-09-04T00:00:00.000Z", "2026-09-03T00:00:00.000Z")), false);
});

test("report token comparison requires an exact, separately configured bearer token", async () => {
  const testToken = Array.from({ length: 8 }, (_, index) => `part-${index}`).join("-");
  const authorized = new Request("https://mcp.zero-slop.ai/internal/counters", {
    headers: { authorization: `Bearer ${testToken}` },
  });
  const wrong = new Request("https://mcp.zero-slop.ai/internal/counters", {
    headers: { authorization: "Bearer wrong" },
  });
  assert.equal(await reportTokenMatches(authorized, testToken), true);
  assert.equal(await reportTokenMatches(wrong, testToken), false);
  assert.equal(await reportTokenMatches(authorized, "short"), false);
});
