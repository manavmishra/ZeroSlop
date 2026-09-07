import assert from "node:assert/strict";
import test from "node:test";
import { handleRest } from "./rest";
import { deslopInputSchema, deslopOutputSchema, openApiDocument, problemSchema } from "./contract";
import type { PipelineResult, WritingReport } from "./types";
import { HostedBudgetError } from "./budget";

const report: WritingReport = {
  score: 0, band: "clear", words: 6, sentences: 1, flaggedPhrases: 0,
  sentenceVariety: "natural", readability: "clear", highWeightFlags: 0,
  punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
  shape: { measured: false, broetry: false, oneSentenceParagraphShare: null, longestFragmentRun: null },
  register: { measured: false, words: 6, checked: 0, findings: [], twoPartContrasts: 0, announcements: 0 }, flags: [],
};
const result: PipelineResult = {
  text: "Maya owns the pricing review.", status: "already_clear", before: report, after: report,
  scoreChange: 0, factsPreserved: true, passedFinalChecks: false, independentModelChecks: 0,
  modelRequests: 0, rolesCompleted: 1, finishingRounds: 0, scorerVersion: "2.10.0", durationMs: 1, note: "No model call needed.",
};
function context() {
  const pending: Promise<unknown>[] = [];
  return { ctx: { waitUntil(promise: Promise<unknown>) { pending.push(promise); } } as ExecutionContext, pending };
}
function environment(allowed = true) {
  const keys: string[] = [];
  const points: AnalyticsEngineDataPoint[] = [];
  // Only the bindings this route uses; the injected pipeline never calls the editor.
  const env = Object.assign({} as Env, {
    SCORER_VERSION: "2.10.0",
    PIPELINE_LIMITER: { async limit({ key }: { key: string }) { keys.push(key); return { success: allowed }; } },
    MCP_COUNTER: { getByName() { return { async fetch() { return Response.json({ ok: true }); } }; } },
    MCP_ANALYTICS: { writeDataPoint(point: AnalyticsEngineDataPoint) { points.push(point); } },
  });
  return { env, keys, points };
}
function request(body: unknown, headers: Record<string, string> = {}) {
  return new Request("https://mcp.zero-slop.ai/v1/deslop", { method: "POST", headers: { "content-type": "application/json", ...headers }, body: JSON.stringify(body) });
}
const neverRun = async (): Promise<PipelineResult> => { throw new Error("pipeline must not run"); };

test("OpenAPI derives its complete input/output contract from runtime schemas", () => {
  const document = openApiDocument("2.10.0");
  assert.equal(document.openapi, "3.1.2");
  assert.equal(document.info.version, "2.10.0");
  assert.equal(document.paths["/v1/deslop"].post.operationId, "deslop");
  const input = document.components.schemas.DeslopInput;
  assert.equal(typeof input.properties?.text === "object" && input.properties.text.maxLength, 20_000);
  assert.equal(typeof input.properties?.audience === "object" && input.properties.audience.maxLength, 200);
  assert.deepEqual(input.required, ["text"]);
  assert.equal(document.components.schemas.DeslopResult.required?.length, 14);
  assert.deepEqual(deslopOutputSchema.parse(result), result);
  assert.deepEqual(deslopInputSchema.parse({ text: "  hello  " }), { text: "hello", genre: "general" });
  assert.equal(deslopInputSchema.safeParse({ text: "😀".repeat(20_000), audience: "😀".repeat(200) }).success, true);
  assert.equal(deslopInputSchema.safeParse({ text: "😀".repeat(20_001) }).success, false);
  assert.equal(deslopInputSchema.safeParse({ text: "draft", audience: "😀".repeat(201) }).success, false);
});

test("all six MCP outcomes preserve all fields over REST, including unapproved outcomes", async () => {
  for (const status of deslopOutputSchema.shape.status.options) {
    const { env, keys } = environment();
    const { ctx, pending } = context();
    const expected = { ...result, status };
    let calls = 0;
    const response = await handleRest(request({ text: "  draft  ", genre: "email", audience: "  team ", unrelated: "ignored" }), env, ctx, async (boundEnv, input) => {
      calls++;
      assert.equal(boundEnv, env);
      assert.deepEqual(input, { text: "draft", genre: "email", audience: "team" });
      return expected;
    });
    assert.equal(response.status, 200);
    assert.equal(calls, 1);
    assert.deepEqual(keys, ["deslop-global"]);
    assert.deepEqual(await response.json(), expected);
    assert.match(response.headers.get("x-request-id") ?? "", /^[0-9a-f-]{36}$/);
    await Promise.all(pending);
  }
});

test("invalid inputs cannot invoke the pipeline or consume inference capacity", async () => {
  for (const body of [{}, { text: " " }, { text: 123 }, [], null, { text: "x".repeat(20_001) }, { text: "x", genre: "invented" }, { text: "x", audience: "x".repeat(201) }]) {
    const { env, keys } = environment();
    const { ctx } = context();
    const response = await handleRest(request(body), env, ctx, neverRun);
    assert.equal(response.status, 400);
    assert.equal(response.headers.get("content-type"), "application/problem+json");
    assert.equal(problemSchema.parse(await response.json()).code, "invalid_input");
    assert.deepEqual(keys, []);
  }
});

test("bad JSON, invalid UTF-8, compressed input and excessive bodies fail safely", async () => {
  const { env } = environment();
  const { ctx } = context();
  for (const [body, headers, expected] of [
    ['{"text":"private draft"', { "content-type": "application/json" }, 400],
    [new Uint8Array([0xff, 0xfe]), { "content-type": "application/json" }, 400],
    ["{}", { "content-type": "text/plain" }, 415],
    ["{}", { "content-type": "application/json", "content-encoding": "gzip" }, 415],
    [" ".repeat(128 * 1024 + 1), { "content-type": "application/json" }, 413],
    ["{}", { "content-type": "application/json", "content-length": "131073" }, 413],
    ["{}", { "content-type": "application/json", "content-length": "not-a-number" }, 400],
  ] as const) {
    const response = await handleRest(new Request("https://mcp.zero-slop.ai/v1/deslop", { method: "POST", headers, body }), env, ctx, neverRun);
    assert.equal(response.status, expected);
    assert.ok(!(await response.text()).includes("private draft"));
  }
});

test("shared capacity returns Retry-After and never runs inference", async () => {
  const { env, keys } = environment(false);
  const { ctx, pending } = context();
  const response = await handleRest(request({ text: "draft" }), env, ctx, neverRun);
  assert.equal(response.status, 429);
  assert.equal(response.headers.get("retry-after"), "10");
  assert.deepEqual(keys, ["deslop-global"]);
  await Promise.all(pending);
});

test("a stalled body times out and does not wait for its cancellation hook", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    cancel() { cancelled = true; return new Promise<void>(() => undefined); },
  });
  const streamed = new Request("https://mcp.zero-slop.ai/v1/deslop", {
    method: "POST", headers: { "content-type": "application/json" }, body, duplex: "half",
  } as RequestInit);
  const { env, keys } = environment();
  const { ctx } = context();
  const responsePromise = handleRest(streamed, env, ctx, neverRun);
  t.mock.timers.tick(10_000);
  const response = await responsePromise;
  assert.equal(response.status, 408);
  assert.equal((await response.json() as { code: string }).code, "body_timeout");
  assert.equal(cancelled, true);
  assert.deepEqual(keys, []);
});

test("streamed bodies are capped even without a declared length", async () => {
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array(100_000));
      controller.enqueue(new Uint8Array(32_000));
    },
    cancel() { cancelled = true; },
  });
  const streamed = new Request("https://mcp.zero-slop.ai/v1/deslop", {
    method: "POST", headers: { "content-type": "application/json" }, body, duplex: "half",
  } as RequestInit);
  const { env, keys } = environment();
  const { ctx } = context();
  const response = await handleRest(streamed, env, ctx, neverRun);
  assert.equal(response.status, 413);
  assert.equal(cancelled, true);
  assert.deepEqual(keys, []);
});

test("exceptions and malformed pipeline outputs never expose draft or stack traces", async () => {
  const { env } = environment();
  const { ctx, pending } = context();
  const response = await handleRest(request({ text: "private original" }), env, ctx, async () => { throw new Error("private original or provider key"); });
  assert.equal(response.status, 503);
  const body = await response.text();
  assert.ok(!body.includes("private original"));
  assert.ok(!body.includes("provider key"));
  const bad = await handleRest(request({ text: "draft" }), env, ctx, async () => ({ ...result, scoreChange: NaN }));
  assert.equal(bad.status, 503);
  await Promise.all(pending);
});

test("REST and OpenAPI advertise supported methods and no cross-origin access", async () => {
  const { env } = environment();
  const { ctx } = context();
  for (const method of ["GET", "PUT", "DELETE", "OPTIONS"]) {
    const response = await handleRest(new Request("https://mcp.zero-slop.ai/v1/deslop", { method }), env, ctx, neverRun);
    assert.equal(response.status, 405);
    assert.equal(response.headers.get("allow"), "POST");
    assert.equal(response.headers.get("access-control-allow-origin"), null);
  }
  const spec = await handleRest(new Request("https://mcp.zero-slop.ai/openapi.json"), env, ctx, neverRun);
  assert.equal(spec.status, 200);
  assert.deepEqual(await spec.json(), openApiDocument(env.SCORER_VERSION));
  const head = await handleRest(new Request("https://mcp.zero-slop.ai/openapi.json", { method: "HEAD" }), env, ctx, neverRun);
  assert.equal(await head.text(), "");
});

test("only exact first-party browser origins receive CORS and preflight access", async () => {
  const { env } = environment(); const { ctx } = context();
  for (const origin of ["https://zero-slop.ai", "https://www.zero-slop.ai"]) {
    const response = await handleRest(new Request("https://mcp.zero-slop.ai/v1/deslop", { method: "OPTIONS", headers: { origin, "access-control-request-method": "POST", "access-control-request-headers": "content-type" } }), env, ctx, neverRun);
    assert.equal(response.status, 204); assert.equal(response.headers.get("access-control-allow-origin"), origin); assert.equal(response.headers.get("access-control-allow-methods"), "POST");
    assert.equal(response.headers.get("access-control-allow-credentials"), null); assert.match(response.headers.get("access-control-expose-headers") ?? "", /Retry-After/);
    assert.match(response.headers.get("vary") ?? "", /Access-Control-Request-Headers/);
    const failure = await handleRest(request({ text: " " }, { origin }), env, ctx, neverRun);
    assert.equal(failure.status, 400); assert.equal(failure.headers.get("access-control-allow-origin"), origin);
  }
  for (const origin of ["https://example.invalid", "https://zero-slop.ai.attacker.invalid", "null", "http://zero-slop.ai", "https://preview.pages.dev", "https://zero-slop.ai/"]) {
    const response = await handleRest(request({ text: "draft" }, { origin }), env, ctx, neverRun);
    assert.equal(response.status, 403); assert.equal(response.headers.get("access-control-allow-origin"), null);
  }
  for (const headers of [{ "access-control-request-method": "GET" }, { "access-control-request-method": "POST", "access-control-request-headers": "content-type, authorization" }]) {
    const response = await handleRest(new Request("https://mcp.zero-slop.ai/v1/deslop", { method: "OPTIONS", headers: { origin: "https://zero-slop.ai", ...headers } }), env, ctx, neverRun);
    assert.equal(response.status, 403); assert.equal(response.headers.get("access-control-allow-methods"), null);
  }
});

test("REST returns structured budget errors with request identity and retry guidance", async () => {
  for (const error of [new HostedBudgetError("usage_limit", 60), new HostedBudgetError("budget_unavailable")]) {
    const { env } = environment(); const { ctx, pending } = context();
    const response = await handleRest(request({ text: "private draft" }, { origin: "https://zero-slop.ai", "cf-connecting-ip": "192.0.2.1" }), env, ctx, async (_env, _input, address) => {
      assert.equal(address, "192.0.2.1"); throw error;
    });
    assert.equal(response.status, error.status); assert.equal(response.headers.get("retry-after"), error.retryAfterSeconds === null ? null : "60");
    assert.equal(response.headers.get("access-control-allow-origin"), "https://zero-slop.ai");
    const body = problemSchema.parse(await response.json()); assert.equal(body.code, error.code); assert.equal(body.requestId, response.headers.get("x-request-id")); assert.ok(!JSON.stringify(body).includes("private draft"));
    await Promise.all(pending);
  }
});

test("REST emits one request and one private aggregate result with measured quality and model use", async () => {
  const { env, points } = environment(); const { ctx, pending } = context();
  const response = await handleRest(request({ text: "private draft" }, { "user-agent": "zero-slop-cli/2", "cf-connecting-ip": "192.0.2.1" }), env, ctx, async () => result);
  assert.equal(response.status, 200);
  assert.deepEqual(points.map((point) => point.blobs?.[1]), ["result", "request"]);
  assert.ok(points.every((point) => point.blobs?.[2] === "rest/deslop" && point.blobs?.[15] === "rest"));
  assert.equal(points[0]?.blobs?.[16], "already_clear"); assert.equal(points[0]?.doubles?.[17], 0);
  assert.equal(points[0]?.doubles?.[2], "private draft".length); assert.equal(points[0]?.doubles?.[8], 0);
  assert.doesNotMatch(JSON.stringify(points), /private|192\.0\.2\.1|requestId|user-agent/);
  await Promise.all(pending);
});

test("REST counts rejected POST attempts once and excludes documentation and preflight traffic", async () => {
  for (const [body, headers] of [[{ text: " " }, {}], [{ text: "draft" }, { origin: "https://foreign.invalid" }]] as const) {
    const { env, points } = environment(); const { ctx } = context();
    await handleRest(request(body, headers), env, ctx, neverRun);
    assert.equal(points.length, 1); assert.equal(points[0]?.blobs?.[1], "request"); assert.equal(points[0]?.blobs?.[4], "error");
  }
  const { env, points } = environment(); const { ctx } = context();
  for (const req of [new Request("https://mcp.zero-slop.ai/openapi.json"), new Request("https://mcp.zero-slop.ai/v1/deslop", { method: "OPTIONS", headers: { origin: "https://zero-slop.ai", "access-control-request-method": "POST" } })]) await handleRest(req, env, ctx, neverRun);
  assert.equal(points.length, 0);
});

test("REST quota and failure outcomes remain separate from completed or approved edits", async () => {
  for (const [allowed, failure, event, approval, calls] of [
    [false, null, "capacity", "limited", 0],
    [true, new HostedBudgetError("usage_limit", 60), "result", "limited", 0],
    [true, new HostedBudgetError("budget_unavailable"), "result", "failed", 0],
    [true, new Error("private failure detail"), "result", "failed", -1],
  ] as const) {
    const { env, points } = environment(allowed); const { ctx, pending } = context();
    await handleRest(request({ text: "private draft" }), env, ctx, async () => { throw failure; });
    assert.equal(points.length, 2); assert.equal(points[0]?.blobs?.[1], event); assert.equal(points[0]?.blobs?.[16], approval); assert.equal(points[0]?.doubles?.[17], calls);
    assert.equal(points[1]?.blobs?.[1], "request"); assert.equal(points[1]?.blobs?.[4], "error");
    assert.doesNotMatch(JSON.stringify(points), /private/);
    await Promise.all(pending);
  }
});
