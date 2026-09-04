import { env } from "cloudflare:workers";
import { evictDurableObject, runInDurableObject } from "cloudflare:test";
import { describe, expect, it } from "vitest";

import { COUNTER_METRICS, McpCounter } from "../src/counter";

describe("McpCounter in workerd", () => {
  it("commits concurrent increments atomically and survives eviction", async () => {
    const stub = env.MCP_COUNTER.getByName(`concurrency-${crypto.randomUUID()}`);
    const increments = 250;
    await Promise.all(Array.from({ length: increments }, () => stub.fetch("https://counter.internal/increment", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ eventId: crypto.randomUUID(), metrics: ["mcp_tool_calls", "messages_deslopped"] }),
    })));

    const response = await stub.fetch("https://counter.internal/snapshot");
    const beforeEviction = await response.json<{
      counters: Record<string, number>;
      startedAt: string | null;
      updatedAt: string | null;
    }>();
    expect(beforeEviction.counters.mcp_tool_calls).toBe(increments);
    expect(beforeEviction.counters.messages_deslopped).toBe(increments);
    expect(beforeEviction.startedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(beforeEviction.updatedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);

    await runInDurableObject(stub, async (instance, state) => {
      expect(instance).toBeInstanceOf(McpCounter);
      const rows = state.storage.sql
        .exec<{ name: string; value: number }>("SELECT name, value FROM counters ORDER BY name")
        .toArray();
      expect(rows).toEqual([
        { name: "mcp_tool_calls", value: increments },
        { name: "messages_deslopped", value: increments },
      ]);
    });

    await evictDurableObject(stub);
    const afterEviction = await (await stub.fetch("https://counter.internal/snapshot")).json<{
      counters: Record<string, number>;
    }>();
    expect(afterEviction.counters.mcp_tool_calls).toBe(increments);
  });

  it("rejects invalid or duplicate metrics without changing storage", async () => {
    const stub = env.MCP_COUNTER.getByName(`validation-${crypto.randomUUID()}`);
    const duplicate = await stub.fetch("https://counter.internal/increment", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ eventId: crypto.randomUUID(), metrics: ["mcp_tool_calls", "mcp_tool_calls"] }),
    });
    const unknown = await stub.fetch("https://counter.internal/increment", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ eventId: crypto.randomUUID(), metrics: ["draft_text"] }),
    });
    expect(duplicate.status).toBe(400);
    expect(unknown.status).toBe(400);

    const snapshot = await (await stub.fetch("https://counter.internal/snapshot")).json<{
      counters: Record<string, number>;
    }>();
    expect(Object.keys(snapshot.counters).sort()).toEqual([...COUNTER_METRICS].sort());
    expect(Object.values(snapshot.counters).every((count) => count === 0)).toBe(true);
  });

  it("deduplicates an ambiguous retry exactly once", async () => {
    const stub = env.MCP_COUNTER.getByName(`retry-${crypto.randomUUID()}`);
    const eventId = crypto.randomUUID();
    const request = () => stub.fetch("https://counter.internal/increment", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ eventId, metrics: ["mcp_tool_calls"] }),
    });
    expect((await request()).status).toBe(204);
    expect((await request()).status).toBe(204);

    const snapshot = await (await stub.fetch("https://counter.internal/snapshot")).json<{
      counters: Record<string, number>;
    }>();
    expect(snapshot.counters.mcp_tool_calls).toBe(1);
  });
});
