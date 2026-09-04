import assert from "node:assert/strict";
import test from "node:test";

import { classifyClient, inspectMcpRequest, telemetryPoint } from "./telemetry";

test("classifies supported clients without retaining the raw user agent", () => {
  assert.equal(classifyClient(undefined, "codex-cli/1.2.3 secret-build-token"), "codex");
  assert.equal(classifyClient("Claude Code", null), "claude-code");
  assert.equal(classifyClient("Claude Cowork", null), "claude-cowork");
  assert.equal(classifyClient("ChatGPT", null), "chatgpt");
});

test("inspects initialize metadata into bounded aggregate categories", async () => {
  const request = new Request("https://mcp.zero-slop.ai/mcp", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      origin: "https://chatgpt.com",
      "user-agent": "raw-agent/very-specific-build",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "initialize",
      params: {
        protocolVersion: "2025-06-18",
        clientInfo: { name: "Codex", version: "42.9.17-private" },
      },
    }),
  });

  const meta = await inspectMcpRequest(request);
  assert.deepEqual(meta, {
    method: "initialize",
    tool: "none",
    client: "codex",
    clientVersion: "42",
    protocolVersion: "2025-06-18",
    country: "unknown",
    colo: "unknown",
    origin: "chatgpt",
    isDeslopCall: false,
  });
  assert.doesNotMatch(JSON.stringify(meta), /very-specific-build|private/);
});

test("telemetry point contains only the documented aggregate schema", () => {
  const meta = {
    method: "tools/call",
    tool: "deslop",
    client: "claude-code",
    clientVersion: "3",
    protocolVersion: "2025-06-18",
    country: "US",
    colo: "SJC",
    origin: "none",
    isDeslopCall: true,
  };
  const point = telemetryPoint(meta, {
    event: "result",
    outcome: "rewritten",
    genre: "professional",
    durationMs: 120,
    inputChars: 500,
    outputChars: 420,
    beforeScore: 78,
    afterScore: 12,
    scoreChange: 66,
    factsPreserved: true,
    finalChecks: true,
    httpStatus: 200,
  });

  assert.equal(point.indexes?.length, 1);
  assert.equal(point.blobs?.length, 15);
  assert.equal(point.doubles?.length, 17);
  assert.deepEqual(point.indexes, ["result:claude-code"]);
  assert.deepEqual(point.blobs?.slice(0, 9), [
    "mcp-v1", "result", "tools/call", "deslop", "rewritten", "claude-code", "3", "2025-06-18", "professional",
  ]);
  const serialized = JSON.stringify(point);
  assert.doesNotMatch(serialized, /prompt|draft|rewrite text|user-agent|ip address/i);
});
