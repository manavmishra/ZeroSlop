import assert from "node:assert/strict";
import test from "node:test";
import worker from "./index";
import { handleRest } from "./rest";
import { deslopInputSchema } from "./contract";
import type { PipelineResult, WritingReport } from "./types";

const report: WritingReport = {
  score: 0, band: "clear", words: 5, sentences: 1, flaggedPhrases: 0,
  sentenceVariety: "natural", readability: "clear", highWeightFlags: 0,
  punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
  shape: { measured: false, broetry: false, oneSentenceParagraphShare: null, longestFragmentRun: null },
  register: { measured: false, words: 5, checked: 0, findings: [], twoPartContrasts: 0, announcements: 0 }, flags: [],
};
const samples = [
  { input: "    The te\u200bxt is clear.", expected: "    The te\u200bxt is clear." },
  { input: "\ufeffHello world.", expected: "\ufeffHello world." },
  { input: "The te\u200bxt is clear. \t\r\n", expected: "The text is clear. \t\r\n" },
];
function environment() {
  return {
    SCORER_VERSION: "2.12.31", ALLOWED_ORIGINS: "https://zero-slop.ai",
    PIPELINE_LIMITER: { async limit() { return { success: true }; } },
    SCORER: { async fetch() { return Response.json(report); } },
  } as unknown as Env;
}
function context() {
  const pending: Promise<unknown>[] = [];
  return { pending, ctx: { waitUntil(promise: Promise<unknown>) { pending.push(promise); } } as ExecutionContext };
}

test("cleanup schema preserves exact whitespace while legacy editing retains trim and size rules", () => {
  for (const sample of samples) assert.equal(deslopInputSchema.parse({ text: sample.input, operation: "clean_text" }).text, sample.input);
  assert.equal(deslopInputSchema.parse({ text: "  hello  " }).text, "hello");
  assert.equal(deslopInputSchema.parse({ text: " ".repeat(100) + "x".repeat(20_000) + " " }).text.length, 20_000);
  assert.equal(deslopInputSchema.safeParse({ text: "x".repeat(20_001) }).success, false);
  assert.equal(deslopInputSchema.safeParse({ text: " " }).success, false);
  assert.equal(deslopInputSchema.safeParse({ text: "x".repeat(20_001), operation: "clean_text" }).success, false);
});

test("REST cleanup preserves raw protected input through schema and the real pipeline", async () => {
  for (const sample of samples) {
    const { ctx, pending } = context();
    const response = await handleRest(new Request("https://mcp.zero-slop.ai/v1/deslop", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: sample.input, operation: "clean_text" }),
    }), environment(), ctx);
    assert.equal(response.status, 200);
    const result = await response.json() as PipelineResult;
    assert.equal(result.text, sample.expected); assert.equal(result.modelRequests, 0);
    await Promise.all(pending);
  }
});

test("MCP cleanup preserves raw protected input through SDK validation and the real pipeline", async () => {
  for (const sample of samples) {
    const { ctx, pending } = context();
    const response = await worker.fetch(new Request("https://mcp.zero-slop.ai/mcp", {
      method: "POST", headers: { "content-type": "application/json", accept: "application/json, text/event-stream", host: "mcp.zero-slop.ai" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "deslop", arguments: { text: sample.input, operation: "clean_text" } } }),
    }), environment(), ctx);
    assert.equal(response.status, 200);
    const body = await response.text();
    const data = body.split("\n").find(line => line.startsWith("data:"));
    const packet = JSON.parse(data ? data.slice(5) : body) as { result?: { structuredContent?: PipelineResult }; error?: unknown };
    assert.equal(packet.error, undefined, body);
    const result = packet.result?.structuredContent;
    assert.ok(result, body); assert.equal(result.text, sample.expected); assert.equal(result.modelRequests, 0);
    await Promise.all(pending);
  }
});

test("MCP tools/list publishes the complete object input schema after preprocessing", async () => {
  const { ctx, pending } = context();
  const response = await worker.fetch(new Request("https://mcp.zero-slop.ai/mcp", {
    method: "POST", headers: { "content-type": "application/json", accept: "application/json, text/event-stream", host: "mcp.zero-slop.ai" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
  }), environment(), ctx);
  assert.equal(response.status, 200);
  const body = await response.text(); const data = body.split("\n").find(line => line.startsWith("data:"));
  const packet = JSON.parse(data ? data.slice(5) : body) as { result: { tools: Array<{ inputSchema: { type?: string; properties?: Record<string, unknown> } }> } };
  const schema = packet.result.tools[0]!.inputSchema;
  assert.equal(schema.type, "object"); assert.ok(schema.properties?.text); assert.ok(schema.properties?.operation);
  await Promise.all(pending);
});
