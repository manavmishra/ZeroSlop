import { env, exports } from "cloudflare:workers";
import { describe, expect, it, vi } from "vitest";

async function rpc(origin: string | undefined, method = "initialize", host = "mcp.zero-slop.ai") {
  return exports.default.fetch(`https://${host}/mcp`, {
    method: "POST",
    headers: {
      host,
      "content-type": "application/json",
      accept: "application/json, text/event-stream",
      ...(origin === undefined ? {} : { origin }),
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method,
      ...(method === "initialize" ? {
        params: {
          protocolVersion: "2025-06-18",
          capabilities: {},
          clientInfo: { name: "origin-regression-test", version: "1.0.0" },
        },
      } : {}),
    }),
  });
}

async function result(response: Response) {
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  expect(response.headers.get("content-type")).toContain("text/event-stream");
  const data = (await response.text()).split("\n").find((line) => line.startsWith("data: "));
  expect(data).toBeDefined();
  const message = JSON.parse(data!.slice("data: ".length));
  expect(message.error).toBeUndefined();
  return message.result;
}

describe("explicit MCP Origin admission in workerd", () => {
  it("adds only the OpenAI platform to the existing production configuration", () => {
    expect(env.ALLOWED_ORIGINS.split(",")).toEqual([
      "https://zero-slop.ai",
      "https://www.zero-slop.ai",
      "https://chatgpt.com",
      "https://claude.ai",
      "https://platform.openai.com",
    ]);
    expect(env.ALLOWED_ORIGINS).not.toContain("*");
  });

  for (const origin of [
    "https://platform.openai.com",
    "https://chatgpt.com",
    "https://claude.ai",
    "https://zero-slop.ai",
    "https://www.zero-slop.ai",
    "http://chatgpt.com",
    "https://claude.ai:8443",
    undefined,
  ]) {
    it(`initializes with ${origin ?? "no Origin"} without inference`, async () => {
      const outbound = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unexpected outbound fetch"));
      try {
        const initialized = await result(await rpc(origin));
        expect(initialized.serverInfo).toEqual({ name: "zero-slop", version: env.SCORER_VERSION });
        expect(initialized.protocolVersion).toBe("2025-06-18");
        expect(outbound).not.toHaveBeenCalled();
      } finally {
        outbound.mockRestore();
      }
    });
  }

  it("discovers the unchanged single tool from the OpenAI platform Origin", async () => {
    const listed = await result(await rpc("https://platform.openai.com", "tools/list"));
    expect(listed.tools).toHaveLength(1);
    expect(listed.tools[0].name).toBe("deslop");
    expect(listed.tools[0].annotations).toMatchObject({
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: false,
    });
    expect(listed.tools[0].inputSchema.properties.text.maxLength).toBe(20_000);
  });

  for (const origin of [
    "https://untrusted.example",
    "https://platform.openai.com.untrusted.example",
    "https://untrusted.platform.openai.com",
    "http://platform.openai.com",
    "https://platform.openai.com:8443",
    "https://platform.openai.com:443",
    "null",
  ]) {
    it(`rejects unadmitted Origin ${origin}`, async () => {
      const response = await rpc(origin);
      expect(response.status).toBe(403);
      expect(response.headers.get("cache-control")).toBe("no-store");
      expect(await response.text()).toMatch(/invalid origin/i);
    });
  }

  it("retains the MCP Host restriction even with an admitted Origin", async () => {
    const response = await rpc("https://platform.openai.com", "initialize", "untrusted.example");
    expect(response.status).toBe(403);
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  for (const origin of ["https://platform.openai.com", "https://chatgpt.com", undefined]) {
    it(`permits existing OPTIONS preflight with ${origin ?? "no Origin"} without inference`, async () => {
      const outbound = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unexpected outbound fetch"));
      try {
        const response = await exports.default.fetch("https://mcp.zero-slop.ai/mcp", {
          method: "OPTIONS",
          headers: {
            host: "mcp.zero-slop.ai",
            "access-control-request-method": "POST",
            "access-control-request-headers": "Content-Type,Accept,MCP-Protocol-Version",
            ...(origin === undefined ? {} : { origin }),
          },
        });
        expect(response.status).toBe(200);
        expect(response.headers.get("cache-control")).toBe("no-store");
        expect(response.headers.get("access-control-allow-origin")).toBe("*");
        expect(response.headers.get("access-control-allow-methods")?.split(",").map((value) => value.trim()).sort())
          .toEqual(["DELETE", "GET", "OPTIONS", "POST"]);
        expect(response.headers.get("access-control-allow-headers")?.split(",").map((value) => value.trim().toLowerCase()).sort())
          .toEqual(["accept", "authorization", "content-type", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id"]);
        expect(outbound).not.toHaveBeenCalled();
      } finally {
        outbound.mockRestore();
      }
    });
  }

  for (const origin of [
    "https://untrusted.example",
    "http://platform.openai.com",
    "https://platform.openai.com:8443",
    "https://platform.openai.com:443",
    "null",
  ]) {
    it(`rejects OPTIONS preflight with unadmitted Origin ${origin}`, async () => {
      const response = await exports.default.fetch("https://mcp.zero-slop.ai/mcp", {
        method: "OPTIONS",
        headers: {
          host: "mcp.zero-slop.ai",
          origin,
          "access-control-request-method": "POST",
        },
      });
      expect(response.status).toBe(403);
      expect(response.headers.get("cache-control")).toBe("no-store");
      expect(await response.text()).toMatch(/invalid origin/i);
    });
  }
});
