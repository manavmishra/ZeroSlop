import assert from "node:assert/strict";
import test from "node:test";
import { editorDiagnosticsSchema, safeEditorDiagnostics } from "./editor-diagnostics";
import { callRole } from "./model";

const env = { EDITOR_ENDPOINT: "https://example.invalid/editor",
  EDITOR_SHARED_SECRET: "synthetic-editor-signing-key-with-40-characters" } as unknown as Env;
const source = "Maya owns the rollout on October 20, and the beta is limited to 25 teams.";
const secret = "PRIVATE_PROVIDER_ERROR_DRAFT_AND_SECRET";

test("diagnostics use only the observed endpoint status and existing bounded attempt fields", () => {
  const input = { endpointHttpStatus: 401, providerAttempts: [
    { provider: "workers-ai", outcome: "unavailable", failureStage: "invoke", httpStatus: 500, message: secret },
    { provider: "openrouter", outcome: "unavailable", failureStage: "http", httpStatus: 429, body: secret, model: secret },
  ] };
  const result = safeEditorDiagnostics(503, input);
  assert.deepEqual(result, { endpointHttpStatus: 503, providerAttempts: [
    { provider: "workers-ai", outcome: "unavailable", failureStage: "invoke" },
    { provider: "openrouter", outcome: "unavailable", failureStage: "http", httpStatus: 429 },
  ] });
  input.providerAttempts[1]!.httpStatus = 401;
  assert.equal(result?.providerAttempts?.[1]?.httpStatus, 429, "entries are copied rather than retained from the payload");
  assert.ok(!JSON.stringify(result).includes(secret));
  assert.ok(editorDiagnosticsSchema.safeParse(result).success);
});

test("unknown endpoint status and malformed provider attempts are omitted", () => {
  for (const status of [undefined, null, "200", NaN, Infinity, 0, 99, 600, 200.5]) {
    assert.equal(safeEditorDiagnostics(status), undefined);
  }
  for (const providerAttempts of [null, {}, [{ provider: secret, outcome: "unavailable" }],
    [{ provider: "workers-ai", outcome: secret }], Array(3).fill({ provider: "workers-ai", outcome: "success" })]) {
    assert.deepEqual(safeEditorDiagnostics(200, { providerAttempts }), { endpointHttpStatus: 200 });
  }
  assert.deepEqual(safeEditorDiagnostics(undefined, { providerAttempts: [{ provider: "openrouter", outcome: "success" }] }),
    { providerAttempts: [{ provider: "openrouter", outcome: "success" }] });
});

test("public diagnostic schema rejects arbitrary fields, excessive attempts and invalid status/stage combinations", () => {
  for (const value of [
    { endpointHttpStatus: "503" }, { endpointHttpStatus: 99 }, { endpointHttpStatus: 600 },
    { endpointHttpStatus: 200.5 }, { endpointHttpStatus: 200, body: secret },
    { providerAttempts: [{ provider: secret, outcome: "unavailable" }] },
    { providerAttempts: Array(3).fill({ provider: "workers-ai", outcome: "success" }) },
    { providerAttempts: [{ provider: "workers-ai", outcome: "success", failureStage: "http" }] },
    { providerAttempts: [{ provider: "workers-ai", outcome: "unavailable", failureStage: "fetch", httpStatus: 500 }] },
    { providerAttempts: [{ provider: "workers-ai", outcome: "unavailable", failureStage: "http", httpStatus: 500, body: secret }] },
  ]) assert.equal(editorDiagnosticsSchema.safeParse(value).success, false);
});

test("parsed HTTP-success diagnostics survive rejection of an unchanged editor reply", async t => {
  const seen: unknown[] = [];
  t.mock.method(globalThis, "fetch", async () => Response.json({ rewrite: source, provider: "mock", model: "mock",
    stored: false, providerCalls: 2, providerAttempts: [
      { provider: "workers-ai", outcome: "invalid_output", message: secret }, { provider: "openrouter", outcome: "success", httpStatus: 200 },
    ] }));
  let count = 0;
  const result = await callRole(env, "complete", source, {}, Date.now() + 2000, "", undefined,
    value => { count = value; }, undefined, value => { seen.push(value); });
  assert.equal(result, null);
  assert.equal(count, 2);
  assert.deepEqual(seen.at(-1), { endpointHttpStatus: 200, providerAttempts: [
    { provider: "workers-ai", outcome: "invalid_output" }, { provider: "openrouter", outcome: "success" },
  ] });
  assert.ok(!JSON.stringify(seen).includes(secret));
});

test("non-OK diagnostics preserve body-consumption boundaries", async t => {
  const seen: unknown[] = [];
  const response = new Response(secret, { status: 400 });
  t.mock.method(globalThis, "fetch", async () => response);
  assert.equal(await callRole(env, "complete", source, {}, Date.now() + 2000, "", undefined,
    undefined, undefined, value => { seen.push(value); }), null);
  assert.equal(response.bodyUsed, false, "additional non-429/503 bodies remain unread");
  assert.deepEqual(seen, [{ endpointHttpStatus: 400 }]);
  globalThis.fetch = (async () => Response.json({ editorOutcome: "unavailable", providerCalls: 2,
    providerAttempts: [{ provider: "openrouter", outcome: "unavailable", failureStage: "http", httpStatus: 403, body: secret }] }, { status: 503 })) as typeof fetch;
  await callRole(env, "complete", source, {}, Date.now() + 2000, "", undefined,
    undefined, undefined, value => { (seen as unknown[]).push(value); });
  assert.deepEqual(seen.at(-1), { endpointHttpStatus: 503, providerAttempts: [
    { provider: "openrouter", outcome: "unavailable", failureStage: "http", httpStatus: 403 },
  ] });
});

test("invalid HTTP-success JSON retains only its observed status", async t => {
  const seen: unknown[] = [];
  t.mock.method(globalThis, "fetch", async () => new Response(secret));
  assert.equal(await callRole(env, "complete", source, {}, Date.now() + 2000, "", undefined,
    undefined, undefined, value => { seen.push(value); }), null);
  assert.deepEqual(seen, [{ endpointHttpStatus: 200 }]);
});

test("no-response failures and pre-request deadline skip do not fabricate diagnostics", async t => {
  const seen: unknown[] = [];
  t.mock.method(globalThis, "fetch", async () => { throw new Error(secret); });
  for (const deadline of [Date.now() + 2000, Date.now()]) {
    assert.equal(await callRole(env, "complete", source, {}, deadline, "", undefined,
      undefined, undefined, value => { seen.push(value); }), null);
  }
  assert.deepEqual(seen, []);
});

for (const late of ["fetch", "body"]) test(`late ${late} completion cannot alter settled diagnostics`, async t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const seen: unknown[] = [];
  let ready!: () => void;
  const entered = new Promise<void>(resolve => { ready = resolve; });
  let resolveFetch!: (response: Response) => void;
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const response = new Response(new ReadableStream<Uint8Array>({
    start(value) { controller = value; },
  }));
  t.mock.method(globalThis, "fetch", () => {
    if (late === "body") return Promise.resolve(response);
    ready();
    return new Promise<Response>(resolve => { resolveFetch = resolve; });
  });
  const pending = callRole(env, "complete", source, {}, Date.now() + 1000, "", undefined,
    undefined, undefined, value => { seen.push(value); if (late === "body") ready(); });
  await entered;
  // Let the observed response status be captured before advancing a body deadline.
  await new Promise<void>(resolve => setImmediate(resolve));
  t.mock.timers.tick(1100);
  assert.equal(await pending, null);
  assert.deepEqual(seen, late === "body" ? [{ endpointHttpStatus: 200 }] : []);
  const snapshot = JSON.stringify(seen);
  const payload = { rewrite: source + " Details follow.", provider: "mock", model: "mock", stored: false,
    providerCalls: 2, providerAttempts: [{ provider: "openrouter", outcome: "success" }] };
  if (late === "fetch") resolveFetch(Response.json(payload));
  else { controller.enqueue(new TextEncoder().encode(JSON.stringify(payload))); controller.close(); }
  await new Promise<void>(resolve => setImmediate(resolve));
  assert.equal(JSON.stringify(seen), snapshot);
});

test("an optional diagnostic callback failure cannot change a usable editor result", async t => {
  t.mock.method(globalThis, "fetch", async () => Response.json({ rewrite: source + " Details follow.",
    provider: "mock", model: "mock", stored: false }));
  assert.ok(await callRole(env, "complete", source, {}, Date.now() + 2000, "", undefined,
    undefined, undefined, () => { throw new Error(secret); }));
});
