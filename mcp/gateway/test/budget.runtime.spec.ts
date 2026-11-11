import { env } from "cloudflare:workers";
import { evictDurableObject, runDurableObjectAlarm, runInDurableObject } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { dailyBudgetClient, EditorBudgetStore } from "../src/budget";

const day = () => new Date().toISOString().slice(0, 10);
const key = (index: number) => index.toString(16).padStart(64, "0");
const reserve = (stub: DurableObjectStub, body: unknown) => stub.fetch("https://counter.internal/reserve-editor", {
  method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
});
const reserveOpenRouter = (stub: DurableObjectStub, body: unknown) => stub.fetch("https://counter.internal/reserve-openrouter", {
  method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
});

describe("shared editor budget in SQLite", () => {
  it("bounds OpenRouter account usage and shares the client allowance with Workers AI", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-openrouter-${crypto.randomUUID()}`);
    const body = { day: day(), clientKey: key(1) };
    expect((await (await reserve(stub, { ...body, neurons: 100 })).json<{ allowed: boolean }>()).allowed).toBe(true);
    expect((await (await reserveOpenRouter(stub, body)).json<{ allowed: boolean }>()).allowed).toBe(true);
    expect((await (await reserveOpenRouter(stub, body)).json<{ allowed: boolean }>()).allowed).toBe(false);
    const all = await Promise.all(Array.from({ length: 810 }, (_, i) => reserveOpenRouter(stub, { day: day(), clientKey: key(i + 2) })));
    const grants = await Promise.all(all.map((response) => response.json<{ allowed: boolean }>()));
    expect(grants.filter((grant) => grant.allowed)).toHaveLength(799);
    await evictDurableObject(stub);
    const denied = await (await reserveOpenRouter(stub, { day: day(), clientKey: key(99) })).json<{ allowed: boolean }>();
    expect(denied.allowed).toBe(false);
    expect((await reserveOpenRouter(stub, { ...body, text: "private draft" })).status).toBe(400);
  });

  it("labels provider and client denials so the editor can choose a safe fallback", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-reasons-${crypto.randomUUID()}`);
    await runInDurableObject(stub, async (_instance, state) => {
      const workers = new EditorBudgetStore(state.storage, Object.assign({}, env, { EDITOR_DAILY_NEURONS: "0" }) as Env);
      const workersDenied = await (await workers.reserve({ day: day(), clientKey: key(1), neurons: 100 })).json();
      expect(workersDenied).toMatchObject({ allowed: false, reason: "workers_daily" });

      const openRouter = new EditorBudgetStore(state.storage, Object.assign({}, env, { EDITOR_OPENROUTER_DAILY_CALLS: "1" }) as Env);
      const openRouterInput = { day: day(), clientKey: key(2) };
      expect(await (await openRouter.reserve(openRouterInput, Date.now, "openrouter")).json()).toMatchObject({ allowed: true });
      expect(await (await openRouter.reserve({ ...openRouterInput, clientKey: key(3) }, Date.now, "openrouter")).json()).toMatchObject({ allowed: false, reason: "openrouter_daily" });

      const client = new EditorBudgetStore(state.storage, Object.assign({}, env, { EDITOR_CLIENT_DAILY_CALLS: "1" }) as Env);
      const clientInput = { day: day(), clientKey: key(4), neurons: 100 };
      expect(await (await client.reserve(clientInput)).json()).toMatchObject({ allowed: true });
      expect(await (await client.reserve(clientInput)).json()).toMatchObject({ allowed: false, reason: "client_daily" });
    });
  });
  it("never overspends the global allowance under concurrent distinct-client requests and eviction", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-global-${crypto.randomUUID()}`);
    const responses = await Promise.all(Array.from({ length: 100 }, (_, index) => reserve(stub, { day: day(), clientKey: key(index), neurons: 100 })));
    const grants = await Promise.all(responses.map((response) => response.json<{ allowed: boolean }>()));
    expect(grants.filter((grant) => grant.allowed)).toHaveLength(80);
    await evictDurableObject(stub);
    const denied = await (await reserve(stub, { day: day(), clientKey: key(101), neurons: 1 })).json<{ allowed: boolean; retryAfterSeconds: number }>();
    expect(denied.allowed).toBe(false); expect(denied.retryAfterSeconds).toBeGreaterThan(0);
    await runInDurableObject(stub, async (_instance, state) => {
      expect(state.storage.sql.exec<{ reserved: number }>("SELECT reserved FROM editor_budget_days").one().reserved).toBe(8000);
      expect(state.storage.sql.exec<{ count: number }>("SELECT COUNT(*) AS count FROM editor_budget_clients").one().count).toBe(80);
      expect(await state.storage.getAlarm()).toBeGreaterThan(Date.now());
    });
  });

  it("grants one expiring Workers AI test reservation while retaining the shared and minute caps", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-test-client-${crypto.randomUUID()}`);
    await runInDurableObject(stub, async (_instance, state) => {
      const now = Date.parse(`${day()}T12:00:00Z`);
      const address = "192.0.2.12";
      const test = await dailyBudgetClient(env.EDITOR_SHARED_SECRET, address, now);
      const other = await dailyBudgetClient(env.EDITOR_SHARED_SECRET, "192.0.2.13", now);
      const unknown = await dailyBudgetClient(env.EDITOR_SHARED_SECRET, "", now);
      const settings = { ...env, EDITOR_CLIENT_DAILY_CALLS: "1", EDITOR_CLIENT_MINUTE_CALLS: "1" };
      const make = (override: string, limit = "8000", dailyCalls = "1") => new EditorBudgetStore(state.storage, {
        ...settings, EDITOR_TEST_CLIENT_OVERRIDE: override, EDITOR_DAILY_NEURONS: limit, EDITOR_CLIENT_DAILY_CALLS: dailyCalls,
      });
      const override = `${test.day} ${address}`;
      const budget = make(override);
      const requestFor = ({ day, key }: typeof test) => ({ day, clientKey: key, neurons: 100 });
      const request = requestFor(test);
      const later = () => now + 60000;
      expect(await (await budget.reserve(request, () => now)).json()).toMatchObject({ allowed: true });
      expect(await (await budget.reserve(request, () => now)).json()).toMatchObject({ reason: "client_minute" });
      expect(await (await budget.reserve({ day: test.day, clientKey: test.key }, later, "openrouter")).json()).toMatchObject({ reason: "client_daily" });
      expect(await (await make(override, "100").reserve(request, later)).json()).toMatchObject({ reason: "workers_daily" });
      expect(await (await make(override, "8000", "0").reserve(request, later)).json()).toMatchObject({ reason: "client_daily" });
      for (const inactive of [`2000-01-01 ${address}`, `${test.day} ${address}/32`, `${override} other`]) {
        expect(await (await make(inactive).reserve(request, later)).json()).toMatchObject({ reason: "client_daily" });
      }
      expect(await (await budget.reserve(requestFor(other), () => now)).json()).toMatchObject({ allowed: true });
      expect(await (await budget.reserve(requestFor(other), later)).json()).toMatchObject({ reason: "client_daily" });
      const scopedAddress = make(`${test.day} fe80::1%en0`);
      expect(await (await scopedAddress.reserve(requestFor(unknown), () => now)).json()).toMatchObject({ allowed: true });
      expect(await (await scopedAddress.reserve(requestFor(unknown), later)).json()).toMatchObject({ reason: "client_daily" });
      const concurrent = await Promise.all([budget.reserve(request, later), budget.reserve(request, later)]);
      const grants = await Promise.all(concurrent.map((response) => response.json<{ allowed: boolean }>()));
      expect(grants.filter(({ allowed }) => allowed)).toHaveLength(1);
      expect(await (await budget.reserve(request, () => now + 120000)).json()).toMatchObject({ reason: "client_daily" });
      expect(state.storage.sql.exec<{ reserved: number }>("SELECT reserved FROM editor_budget_days").one().reserved).toBe(400);
    });
  });

  it("atomically enforces the per-client minute allowance across all callers", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-client-${crypto.randomUUID()}`);
    const responses = await Promise.all(Array.from({ length: 20 }, () => reserve(stub, { day: day(), clientKey: key(1), neurons: 100 })));
    const grants = await Promise.all(responses.map((response) => response.json<{ allowed: boolean; retryAfterSeconds: number }>()));
    expect(grants.filter((grant) => grant.allowed)).toHaveLength(2);
    expect(grants.filter((grant) => !grant.allowed).every((grant) => grant.retryAfterSeconds >= 1 && grant.retryAfterSeconds <= 60)).toBe(true);
    await runInDurableObject(stub, async (_instance, state) => {
      expect(state.storage.sql.exec<{ reserved: number }>("SELECT reserved FROM editor_budget_days").one().reserved).toBe(200);
    });
  });

  it("resets minute counts, retains daily caps, and discards yesterday's pseudonyms", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-reset-${crypto.randomUUID()}`);
    await runInDurableObject(stub, async (_instance, state) => {
      const budget = new EditorBudgetStore(state.storage, env);
      const noon = Math.floor(Date.now() / 86400000) * 86400000 + 10 * 86400000 + 12 * 3600000;
      const futureDay = new Date(noon).toISOString().slice(0, 10);
      for (let index = 0; index < 5; index++) {
        const grant = await (await budget.reserve({ day: futureDay, clientKey: key(1), neurons: 100 }, () => noon + index * 60000)).json<{ allowed: boolean }>();
        expect(grant.allowed).toBe(true);
      }
      const denied = await (await budget.reserve({ day: futureDay, clientKey: key(1), neurons: 100 }, () => noon + 6 * 60000)).json<{ allowed: boolean }>();
      expect(denied.allowed).toBe(false);
      const nextDay = new Date(noon + 86400000).toISOString().slice(0, 10);
      const reset = await (await budget.reserve({ day: nextDay, clientKey: key(2), neurons: 100 }, () => noon + 86400000)).json<{ allowed: boolean }>();
      expect(reset.allowed).toBe(true);
      expect(state.storage.sql.exec<{ day: string; client_key: string }>("SELECT day, client_key FROM editor_budget_clients").toArray()).toEqual([{ day: nextDay, client_key: key(2) }]);
      expect(state.storage.sql.exec<{ reserved: number }>("SELECT reserved FROM editor_budget_days").one().reserved).toBe(100);
    });
  });

  it("rejects malformed, stale, inflated and extra-field reservations without state writes", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-invalid-${crypto.randomUUID()}`);
    const valid = { day: day(), clientKey: key(1), neurons: 100 };
    for (const input of [null, [], {}, { ...valid, day: "2020-01-01" }, { ...valid, neurons: 0 }, { ...valid, neurons: -1 }, { ...valid, neurons: 8001 }, { ...valid, neurons: 0.5 }, { ...valid, clientKey: "192.0.2.1" }, { ...valid, text: "must not be stored" }]) expect((await reserve(stub, input)).status).toBe(400);
    expect((await reserve(stub, { ...valid, text: "x".repeat(1000) })).status).toBe(503);
    await runInDurableObject(stub, async (_instance, state) => {
      expect(state.storage.sql.exec<{ count: number }>("SELECT COUNT(*) AS count FROM editor_budget_days").one().count).toBe(0);
      expect(state.storage.sql.exec<{ count: number }>("SELECT COUNT(*) AS count FROM editor_budget_clients").one().count).toBe(0);
    });
  });

  it("supports a lower or zero allowance and rejects configuration above the hard ceiling", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-config-${crypto.randomUUID()}`);
    await runInDurableObject(stub, async (_instance, state) => {
      const make = (value: string) => new EditorBudgetStore(state.storage, Object.assign({}, env, { EDITOR_DAILY_NEURONS: value }) as Env);
      const input = { day: day(), clientKey: key(1), neurons: 100 };
      expect(await (await make("0").reserve(input)).json()).toMatchObject({ allowed: false });
      expect(await (await make("100").reserve(input)).json()).toMatchObject({ allowed: true });
      expect(await (await make("100").reserve({ ...input, clientKey: key(2) })).json()).toMatchObject({ allowed: false });
      for (const invalid of ["8001", "-1", "8e3", "NaN", ""]) await expect(make(invalid).reserve(input)).rejects.toThrow("invalid_budget_configuration");
    });
  });

  it("purges expired quota data on its alarm without touching lifetime counters", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-alarm-${crypto.randomUUID()}`);
    await reserve(stub, { day: day(), clientKey: key(1), neurons: 100 });
    await runInDurableObject(stub, async (_instance, state) => {
      state.storage.sql.exec("INSERT INTO editor_budget_days VALUES ('2020-01-01', 500)");
      state.storage.sql.exec("INSERT INTO editor_budget_clients VALUES ('2020-01-01', ?, 1, 1, 1)", key(3));
      state.storage.sql.exec("INSERT INTO counters VALUES ('mcp_tool_calls', 7)");
    });
    expect(await runDurableObjectAlarm(stub)).toBe(true);
    await runInDurableObject(stub, async (_instance, state) => {
      expect(state.storage.sql.exec<{ day: string }>("SELECT day FROM editor_budget_clients").toArray()).toEqual([{ day: day() }]);
      expect(state.storage.sql.exec<{ value: number }>("SELECT value FROM counters WHERE name = 'mcp_tool_calls'").one().value).toBe(7);
    });
  });

  it("blocks the last UTC minute and never grants a request which crosses midnight during storage work", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-midnight-${crypto.randomUUID()}`);
    await runInDurableObject(stub, async (_instance, state) => {
      const budget = new EditorBudgetStore(state.storage, env);
      const midnight = (Math.floor(Date.now() / 86400000) + 10) * 86400000;
      const input = { day: new Date(midnight - 61000).toISOString().slice(0, 10), clientKey: key(1), neurons: 100 };
      const near = await (await budget.reserve(input, () => midnight - 60000)).json();
      expect(near).toEqual({ allowed: false, retryAfterSeconds: 60, reason: "day_reset" });
      let ticks = 0;
      await expect(budget.reserve(input, () => ticks++ === 0 ? midnight - 61000 : midnight + 1)).rejects.toThrow("budget_day_changed");
      expect(state.storage.sql.exec<{ count: number }>("SELECT COUNT(*) AS count FROM editor_budget_days").one().count).toBe(0);
    });
  });

  it("never grants if expiration cannot be read or durably scheduled", async () => {
    const stub = env.MCP_COUNTER.getByName(`budget-alarm-failure-${crypto.randomUUID()}`);
    await runInDurableObject(stub, async (_instance, state) => {
      for (const failingOperation of ["getAlarm", "setAlarm"]) {
        const storage = {
          sql: state.storage.sql,
          transactionSync: state.storage.transactionSync.bind(state.storage),
          getAlarm: async () => { if (failingOperation === "getAlarm") throw new Error("synthetic_alarm_failure"); return null; },
          setAlarm: async () => { throw new Error("synthetic_alarm_failure"); },
        } as unknown as DurableObjectStorage;
        const budget = new EditorBudgetStore(storage, env);
        const noon = Math.floor(Date.now() / 86400000) * 86400000 + 12 * 3600000;
        await expect(budget.reserve({ day: new Date(noon).toISOString().slice(0, 10), clientKey: key(1), neurons: 100 }, () => noon)).rejects.toThrow("synthetic_alarm_failure");
        expect(state.storage.sql.exec<{ count: number }>("SELECT COUNT(*) AS count FROM editor_budget_days").one().count).toBe(0);
        expect(state.storage.sql.exec<{ count: number }>("SELECT COUNT(*) AS count FROM editor_budget_clients").one().count).toBe(0);
      }
    });
  });
});
