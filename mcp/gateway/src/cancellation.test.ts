import assert from "node:assert/strict";
import test from "node:test";
import { randomBytes } from "node:crypto";
import { boundedOperation, PipelineCancelledError } from "./cancellation";
import { callRole } from "./model";
import { runPipeline } from "./pipeline";
import worker from "./index";

test("already-cancelled requests cannot begin any scorer or model work", async () => {
  const controller = new AbortController(); controller.abort();
  let calls = 0;
  const env = { SCORER: { fetch() { calls++; throw new Error("must_not_start"); } } } as unknown as Env;
  await assert.rejects(runPipeline(env, { text: "synthetic", genre: "general" }, "", controller.signal),
    (error: unknown) => error instanceof PipelineCancelledError && error.modelRequests === 0);
  assert.equal(calls, 0);
});

test("a scorer ignoring abort cannot hold a cancelled pipeline open or start editing later", async () => {
  const controller = new AbortController();
  let release!: (response: Response) => void;
  let signal: AbortSignal | undefined;
  const env = { SCORER: { fetch(_url: unknown, init: RequestInit) {
    signal = init.signal!;
    return new Promise<Response>((resolve) => { release = resolve; });
  } } } as unknown as Env;
  const operation = runPipeline(env, { text: "synthetic", genre: "general" }, "", controller.signal);
  controller.abort();
  await assert.rejects(operation, (error: unknown) => error instanceof PipelineCancelledError && error.modelRequests === 0);
  assert.equal(signal?.aborted, true);
  release(Response.json({ invalid: "late scorer response" }));
  await new Promise((resolve) => setTimeout(resolve, 0));
});

test("explicit deadline settles even when the upstream never observes its abort signal", async () => {
  let upstreamSignal: AbortSignal | undefined;
  await assert.rejects(boundedOperation(async (signal) => {
    upstreamSignal = signal;
    return new Promise(() => {});
  }, 15), /upstream_deadline/);
  assert.equal(upstreamSignal?.aborted, true);
});

test("bounded operation detaches the caller listener after success, failure, timeout and cancellation", async () => {
  for (const mode of ["success", "failure", "timeout", "cancel"]) {
    const controller = new AbortController();
    let added = 0; let removed = 0;
    const add = controller.signal.addEventListener.bind(controller.signal);
    const remove = controller.signal.removeEventListener.bind(controller.signal);
    controller.signal.addEventListener = (...args: Parameters<AbortSignal["addEventListener"]>) => { added++; return add(...args); };
    controller.signal.removeEventListener = (...args: Parameters<AbortSignal["removeEventListener"]>) => { removed++; return remove(...args); };
    const operation = boundedOperation(async () => {
      if (mode === "success") return 1;
      if (mode === "failure") throw new Error("synthetic");
      return new Promise<number>(() => {});
    }, 5, { signal: controller.signal, editorRequested: false });
    if (mode === "cancel") controller.abort();
    if (mode === "success") assert.equal(await operation, 1);
    else await assert.rejects(operation);
    assert.equal(added, 1); assert.equal(removed, 1);
  }
});

test("editor cancellation before signing completes starts zero requests", async () => {
  const controller = new AbortController();
  const control = { signal: controller.signal, editorRequested: false };
  const pending = callRole({ EDITOR_SHARED_SECRET: randomBytes(32).toString("hex") } as Env,
    "complete", "synthetic", {}, Date.now() + 5000, "", control);
  controller.abort();
  await assert.rejects(pending, (error: unknown) => error instanceof PipelineCancelledError && error.modelRequests === 0);
  assert.equal(control.editorRequested, false);
});

test("editor cancellation after dispatch stays uncertain, aborts the upstream and never retries", async () => {
  const originalFetch = globalThis.fetch;
  const controller = new AbortController();
  let started!: () => void;
  const ready = new Promise<void>((resolve) => { started = resolve; });
  let calls = 0; let signal: AbortSignal | undefined;
  globalThis.fetch = (async (_url: unknown, init: RequestInit) => {
    calls++; signal = init.signal!; started(); return new Promise<Response>(() => {});
  }) as typeof fetch;
  try {
    const pending = callRole({ EDITOR_SHARED_SECRET: randomBytes(32).toString("hex"), EDITOR_ENDPOINT: "https://editor.invalid" } as unknown as Env,
      "complete", "synthetic", {}, Date.now() + 5000, "", { signal: controller.signal, editorRequested: false });
    await ready; controller.abort();
    await assert.rejects(pending, (error: unknown) => error instanceof PipelineCancelledError && error.modelRequests === -1);
    assert.equal(calls, 1); assert.equal(signal?.aborted, true);
  } finally { globalThis.fetch = originalFetch; }
});

test("successive upstream phases share one global deadline instead of restarting the allowance", async () => {
  const control = { editorRequested: false, deadline: Date.now() + 40 };
  await boundedOperation(() => new Promise((resolve) => setTimeout(resolve, 25)), 8000, control);
  const started = Date.now();
  await assert.rejects(boundedOperation(() => new Promise(() => {}), 8000, control), /upstream_deadline/);
  assert.ok(Date.now() - started < 1000);
  let calls = 0;
  await assert.rejects(boundedOperation(async () => { calls++; }, 8000, { ...control, deadline: Date.now() - 1 }), /upstream_deadline/);
  assert.equal(calls, 0);
});

test("a stalled MCP body gets a sanitized 408 without reaching limiter, scorer or editor", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let calls = 0;
  const env = { PIPELINE_LIMITER: { limit() { calls++; throw new Error("must_not_start"); } } } as unknown as Env;
  const request = new Request("https://mcp.zero-slop.ai/mcp", {
    method: "POST", body: new ReadableStream({ pull() { return new Promise(() => {}); }, cancel() { return new Promise(() => {}); } }),
    duplex: "half",
  } as RequestInit);
  const pending = worker.fetch(request, env, {} as ExecutionContext);
  t.mock.timers.tick(10_000);
  const response = await pending;
  assert.equal(response.status, 408);
  assert.deepEqual(await response.json(), { error: "body_timeout", message: "The MCP request body must arrive within 10 seconds." });
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(calls, 0);
});

test("a cancelled MCP body cannot reach the coarse limiter or inference", async () => {
  const controller = new AbortController();
  const request = new Request("https://mcp.zero-slop.ai/mcp", {
    method: "POST", body: new ReadableStream({ pull() { return new Promise(() => {}); } }),
    signal: controller.signal, duplex: "half",
  } as RequestInit);
  const pending = worker.fetch(request, {} as Env, {} as ExecutionContext);
  controller.abort();
  const response = await pending;
  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { error: "invalid_request", message: "The MCP request body could not be read." });
});
