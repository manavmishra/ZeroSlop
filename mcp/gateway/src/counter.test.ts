import assert from "node:assert/strict";
import test from "node:test";

import {
  countMcpRequest,
  countPipelineResult,
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

function counterEnv(recorded: string[][]): Env {
  return {
    MCP_COUNTER: {
      getByName() {
        return {
          async fetch(_input: RequestInfo | URL, init?: RequestInit) {
            const body = JSON.parse(String(init?.body)) as { metrics: string[] };
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

test("report token comparison requires an exact, separately configured bearer token", () => {
  const testToken = Array.from({ length: 8 }, (_, index) => `part-${index}`).join("-");
  const authorized = new Request("https://mcp.zero-slop.ai/internal/counters", {
    headers: { authorization: `Bearer ${testToken}` },
  });
  const wrong = new Request("https://mcp.zero-slop.ai/internal/counters", {
    headers: { authorization: "Bearer wrong" },
  });
  assert.equal(reportTokenMatches(authorized, testToken), true);
  assert.equal(reportTokenMatches(wrong, testToken), false);
  assert.equal(reportTokenMatches(authorized, "short"), false);
});
