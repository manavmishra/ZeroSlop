import assert from "node:assert/strict";
import test from "node:test";

import worker from "./index";

function signingKeyForTests(): string {
  return Array.from({ length: 40 }, (_, index) => String.fromCharCode(97 + (index % 26))).join("");
}

function healthEnv(scorerVersion: string): Env {
  return {
    SCORER_VERSION: "2.8.7",
    EDITOR_SHARED_SECRET: signingKeyForTests(),
    SCORER: {
      fetch: async () => Response.json({ ok: true, scorerVersion }),
    },
  } as unknown as Env;
}

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
    healthEnv("2.8.7"),
    {} as ExecutionContext,
  );

  assert.equal(response.status, 200);
  assert.equal((await response.json() as { ok: boolean }).ok, true);
});

test("health fails closed when connector signing is not configured", async () => {
  const env = healthEnv("2.8.7");
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
    version: "2.8.7",
    scorer: { ok: true, scorerVersion: "2.8.7" },
    editorConfigured: false,
  });
});
