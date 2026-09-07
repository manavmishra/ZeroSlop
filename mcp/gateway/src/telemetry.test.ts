import assert from "node:assert/strict";
import test from "node:test";

import { classifyClient, inspectMcpRequest, inspectRestRequest, telemetryPoint, resultApproval, trackPipelineResult, trackPipelineFailure } from "./telemetry";
import type { PipelineResult, WritingReport } from "./types";

test("classifies supported clients without retaining the raw user agent", () => {
  assert.equal(classifyClient(undefined, "codex-cli/1.2.3 secret-build-token"), "codex");
  assert.equal(classifyClient("Claude Code", null), "claude-code");
  assert.equal(classifyClient("Claude Cowork", null), "claude-cowork");
  assert.equal(classifyClient("ChatGPT", null), "chatgpt");
  assert.equal(classifyClient("zero-slop-cli", null), "zero-slop-cli");
  assert.equal(classifyClient(undefined, "zero-slop-cli/2"), "zero-slop-cli");
  for (const value of ["node", "zero-slop-raycast/2", "zero-slop-cli/2 private-token", "pretend-zero-slop-cli/2"]) assert.equal(classifyClient(undefined, value), "unknown");
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
    channel: "mcp",
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
  assert.equal(point.blobs?.length, 17);
  assert.equal(point.doubles?.length, 18);
  assert.deepEqual(point.indexes, ["result:claude-code"]);
  assert.deepEqual(point.blobs?.slice(0, 9), [
    "mcp-v1", "result", "tools/call", "deslop", "rewritten", "claude-code", "3", "2025-06-18", "professional",
  ]);
  assert.deepEqual(point.blobs?.slice(15), ["mcp", "none"]);
  assert.equal(point.doubles?.[17], -1, "unknown model usage must not become zero");
  const serialized = JSON.stringify(point);
  assert.doesNotMatch(serialized, /prompt|draft|rewrite text|user-agent|ip address/i);
});

test("stateless CLI tool calls are attributable without retaining header or draft data", async () => {
  const request = new Request("https://mcp.zero-slop.ai/mcp", { method: "POST", headers: { "user-agent": "zero-slop-cli/2", "cf-connecting-ip": "192.0.2.1", "x-user-id": "private-identifier" }, body: JSON.stringify({ method: "tools/call", params: { name: "deslop", arguments: { text: "private source draft" } } }) });
  const meta = await inspectMcpRequest(request);
  assert.equal(meta.channel, "cli"); assert.equal(meta.clientVersion, "2"); assert.equal(meta.isDeslopCall, true);
  assert.doesNotMatch(JSON.stringify(meta), /192\.0\.2\.1|private|zero-slop-cli\/2/);
  const hostile = await inspectMcpRequest(new Request(request.url, { method: "POST", body: JSON.stringify({ method: "tools/call", params: { name: "private-draft-as-tool-name" } }) }));
  assert.equal(hostile.tool, "other"); assert.equal(hostile.isDeslopCall, false); assert.doesNotMatch(JSON.stringify(hostile), /private/);
  const rest = inspectRestRequest(request);
  assert.equal(rest.channel, "rest"); assert.equal(rest.client, "rest-api"); assert.equal(rest.method, "rest/deslop");
});

const report: WritingReport = {
  score: 5, band: "clear", words: 6, sentences: 1, flaggedPhrases: 0, sentenceVariety: "natural", readability: "clear", highWeightFlags: 0,
  punctuation: { dashes: 0, emoji: 0, hashtags: 0 }, shape: { measured: false, broetry: false, oneSentenceParagraphShare: null, longestFragmentRun: null },
  register: { measured: false, words: 6, checked: 0, findings: [], twoPartContrasts: 0, announcements: 0 }, flags: [],
};
const result: PipelineResult = {
  text: "private rewritten source", status: "rewritten", before: { ...report, score: 70 }, after: report, scoreChange: 65,
  factsPreserved: true, passedFinalChecks: true, independentModelChecks: 0, modelRequests: 1, rolesCompleted: 1, finishingRounds: 0, scorerVersion: "2.10.1", durationMs: 123, note: "private note",
};

test("approval separates a completed response from an approved rewrite and review warnings", () => {
  assert.equal(resultApproval(result), "approved_rewrite");
  const clear = { ...result, status: "already_clear" as const, before: report, scoreChange: 0, passedFinalChecks: false, modelRequests: 0 };
  assert.equal(resultApproval(clear), "already_clear");
  for (const value of [{ ...result, passedFinalChecks: false }, { ...result, factsPreserved: false }, { ...clear, modelRequests: 1 }, { ...clear, scoreChange: 1 }, { ...clear, before: { ...report, score: 10 } }]) assert.equal(resultApproval(value), "review_required");
  for (const status of ["rewritten_with_warnings", "unchanged_no_better_version", "unchanged_verification_failed", "unchanged_service_unavailable"] as const) assert.equal(resultApproval({ ...result, status }), "review_required");
});

test("result and quota metrics preserve numbers without prose or unknown model-count guesses", () => {
  const points: AnalyticsEngineDataPoint[] = [];
  const env = Object.assign({} as Env, { MCP_ANALYTICS: { writeDataPoint(point: AnalyticsEngineDataPoint) { points.push(point); } } });
  const meta = inspectRestRequest(new Request("https://mcp.zero-slop.ai/v1/deslop"));
  trackPipelineResult(env, meta, "email", 500, result);
  assert.equal(points[0]?.blobs?.[15], "rest"); assert.equal(points[0]?.blobs?.[16], "approved_rewrite");
  assert.equal(points[0]?.doubles?.[1], 123); assert.equal(points[0]?.doubles?.[2], 500); assert.equal(points[0]?.doubles?.[8], 65); assert.equal(points[0]?.doubles?.[17], 1);
  trackPipelineFailure(env, meta, "email", 500, 12, "usage_limit");
  trackPipelineFailure(env, meta, "email", 500, 12, "budget_unavailable");
  trackPipelineFailure(env, meta, "email", 500, 12);
  assert.deepEqual(points.slice(1).map((point) => [point.blobs?.[4], point.blobs?.[16], point.doubles?.[16], point.doubles?.[17]]), [["usage_limit", "limited", 429, 0], ["budget_unavailable", "failed", 503, 0], ["failed", "failed", 503, -1]]);
  assert.doesNotMatch(JSON.stringify(points), /private|note|source/);
});

test("analytics failure cannot fail delivery or log arbitrary binding text", (t) => {
  const logs: unknown[] = [];
  t.mock.method(console, "warn", (value: unknown) => logs.push(value));
  const env = Object.assign({} as Env, { MCP_ANALYTICS: { writeDataPoint() { throw new Error("private draft or credential"); } } });
  assert.doesNotThrow(() => trackPipelineResult(env, inspectRestRequest(new Request("https://mcp.zero-slop.ai/v1/deslop")), "general", 1, result));
  assert.doesNotMatch(JSON.stringify(logs), /private|credential/);
});
