import { env } from "cloudflare:workers";
import { describe, expect, it } from "vitest";
import worker from "../src/index";

describe("REST routes in workerd", () => {
  const ctx = { waitUntil() {} } as ExecutionContext;
  it("serves the generated public OpenAPI document through the real entrypoint", async () => {
    const response = await worker.fetch(new Request("https://mcp.zero-slop.ai/openapi.json"), env, ctx);
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    const schema = await response.json() as { openapi: string; paths: Record<string, unknown> };
    expect(schema.openapi).toBe("3.1.2");
    expect(schema.paths["/v1/deslop"]).toBeDefined();
  });
  it("rejects invalid drafts without calling the editor or scorer", async () => {
    const response = await worker.fetch(new Request("https://mcp.zero-slop.ai/v1/deslop", {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ text: " " }),
    }), env, ctx);
    expect(response.status).toBe(400);
    expect(response.headers.get("content-type")).toBe("application/problem+json");
    expect(response.headers.get("cache-control")).toBe("no-store");
  });
});
