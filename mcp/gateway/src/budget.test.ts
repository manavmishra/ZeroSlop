import assert from "node:assert/strict";
import { createHmac, randomBytes } from "node:crypto";
import test from "node:test";
import { dailyBudgetClient, HostedBudgetError } from "./budget";
import { callRole } from "./model";

const secret = randomBytes(32).toString("hex");
const environment = Object.assign({} as Env, { EDITOR_SHARED_SECRET: secret, EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite" });

test("hosted limit messages explain waiting without inventing a traffic cause", () => {
  const limited = new HostedBudgetError("usage_limit", 60);
  assert.match(limited.message, /temporarily busy or at its free usage limit/);
  assert.match(limited.message, /Please wait at least 60 seconds before trying again/);
  assert.match(new HostedBudgetError("usage_limit", 1).message, /at least 1 second before/);
  assert.match(new HostedBudgetError("usage_limit").message, /Please try again later/);
  const unavailable = new HostedBudgetError("budget_unavailable");
  assert.match(unavailable.message, /Hosted capacity could not be checked/);
  assert.match(unavailable.message, /No model request was started/);
  assert.doesNotMatch(unavailable.message, /busy|heavy traffic/i);
});

test("the gateway and demo identity protocol uses a daily keyed hash and a bounded unknown bucket", async () => {
  const day = "2026-09-07"; const now = Date.parse(`${day}T12:00:00Z`);
  const client = await dailyBudgetClient(secret, "192.0.2.1", now);
  assert.equal(client.key, createHmac("sha256", secret).update(`zero-slop-editor-client-v1\n${day}\n192.0.2.1`).digest("hex"));
  assert.notDeepEqual(client, await dailyBudgetClient(secret, "192.0.2.1", now + 86400000));
  assert.deepEqual(await dailyBudgetClient(secret, "", now), await dailyBudgetClient(secret, "spoofed host", now));
  await assert.rejects(dailyBudgetClient("short"), HostedBudgetError);
});

test("signed editor bodies carry the derived daily key without forwarding raw IP", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async (_input, init) => {
    calls++;
    const body = JSON.parse(String(init?.body));
    assert.deepEqual(body.budgetClient, await dailyBudgetClient(secret, "192.0.2.1"));
    assert.ok(!String(init?.body).includes("192.0.2.1"));
    return Response.json({ rewrite: "Maya owns the report and Omar will review it on Friday.", stored: false, provider: "workers-ai", model: "synthetic" });
  };
  try {
    await callRole(environment, "complete", "It is important to note that Maya owns the report and Omar will review it on Friday.", {}, Date.now() + 1000, "192.0.2.1");
    assert.equal(calls, 1);
  } finally { globalThis.fetch = original; }
});

test("editor quota and unavailable-gate responses propagate without retries or a local success", async () => {
  const original = globalThis.fetch;
  try {
    for (const [status, code, retry, expectedCode] of [[429, "usage_limit", "60", "usage_limit"], [503, "budget_unavailable", null, "budget_unavailable"], [429, "usage_limit", "0", "budget_unavailable"], [429, "usage_limit", "100000", "budget_unavailable"], [429, "usage_limit", "tomorrow", "budget_unavailable"]] as const) {
      let calls = 0;
      globalThis.fetch = async () => { calls++; return Response.json({ code, detail: "untrusted provider text" }, { status, headers: retry === null ? {} : { "retry-after": retry } }); };
      await assert.rejects(callRole(environment, "complete", "A draft that needs editing.", {}, Date.now() + 1000), (error: unknown) => {
        assert.ok(error instanceof HostedBudgetError); assert.equal(error.code, expectedCode); assert.ok(!error.message.includes("untrusted provider text"));
        assert.equal(error.retryAfterSeconds, expectedCode === "usage_limit" ? 60 : null); return true;
      });
      assert.equal(calls, 1);
    }
  } finally { globalThis.fetch = original; }
});

test("missing connector secret fails before network work", async () => {
  const original = globalThis.fetch; let calls = 0;
  globalThis.fetch = async () => { calls++; throw new Error("must not fetch"); };
  try {
    await assert.rejects(callRole(Object.assign({}, environment, { EDITOR_SHARED_SECRET: "" }), "complete", "Draft", {}, Date.now() + 1000), HostedBudgetError);
    assert.equal(calls, 0);
  } finally { globalThis.fetch = original; }
});
