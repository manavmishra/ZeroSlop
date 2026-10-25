import { exports } from "cloudflare:workers";
import { describe, expect, it } from "vitest";

// Claude Code opens `subscriptions/listen` whenever a 2026-07-28 server
// advertises `tools.listChanged`. The SDK then holds the stream open with a
// keepalive every 15 seconds, and on the Workers Free plan that stream ran
// past the 10 ms CPU limit. The tool list never changes at runtime, so the
// gateway advertises no change notifications and closes any listen request
// as soon as it is acknowledged.

const MODERN = "2026-07-28";
const envelope = {
  "io.modelcontextprotocol/protocolVersion": MODERN,
  "io.modelcontextprotocol/clientInfo": { name: "claude-code", version: "2.1.0" },
  "io.modelcontextprotocol/clientCapabilities": {},
};

function modernRpc(method: string, id: string | number, params: Record<string, unknown> = {}) {
  return exports.default.fetch("https://mcp.zero-slop.ai/mcp", {
    method: "POST",
    headers: {
      host: "mcp.zero-slop.ai",
      "content-type": "application/json",
      accept: "application/json, text/event-stream",
      "mcp-method": method,
      "mcp-protocol-version": MODERN,
    },
    body: JSON.stringify({ jsonrpc: "2.0", id, method, params: { _meta: envelope, ...params } }),
  });
}

function sseMessages(body: string): Array<Record<string, any>> {
  return body.split("\n").filter((line) => line.startsWith("data: ")).map((line) => JSON.parse(line.slice(6)));
}

async function textWithin(response: Response, ms: number): Promise<string> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`response body still open after ${ms} ms`)), ms);
  });
  try {
    return await Promise.race([response.text(), deadline]);
  } finally {
    clearTimeout(timer);
    await response.body?.cancel().catch(() => undefined);
  }
}

describe("MCP change notifications in workerd", () => {
  it("advertises no tool-list change notifications to modern clients", async () => {
    const response = await modernRpc("server/discover", "discover-1");
    expect(response.status).toBe(200);
    const message = JSON.parse(await textWithin(response, 2000)) as { result: { capabilities: { tools?: { listChanged?: boolean } } } };
    expect(message.result.capabilities.tools).toEqual({ listChanged: false });
  });

  it("advertises no tool-list change notifications to 2025-era clients", async () => {
    const response = await exports.default.fetch("https://mcp.zero-slop.ai/mcp", {
      method: "POST",
      headers: { host: "mcp.zero-slop.ai", "content-type": "application/json", accept: "application/json, text/event-stream" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "claude-code", version: "2.1.0" } },
      }),
    });
    const [message] = sseMessages(await textWithin(response, 2000));
    expect(message?.result.capabilities.tools).toEqual({ listChanged: false });
  });

  it("acknowledges a listen request and completes it at once instead of holding a stream", async () => {
    const response = await modernRpc("subscriptions/listen", "listen:0", { notifications: { toolsListChanged: true } });
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/event-stream");
    expect(response.headers.get("cache-control")).toBe("no-store");
    const messages = sseMessages(await textWithin(response, 1000));
    expect(messages).toHaveLength(2);
    expect(messages[0]).toMatchObject({
      method: "notifications/subscriptions/acknowledged",
      params: { notifications: {}, _meta: { "io.modelcontextprotocol/subscriptionId": "listen:0" } },
    });
    expect(messages[1]).toMatchObject({
      id: "listen:0",
      result: {
        resultType: "complete",
        _meta: {
          "io.modelcontextprotocol/subscriptionId": "listen:0",
          "io.modelcontextprotocol/serverInfo": { name: "zero-slop" },
        },
      },
    });
  });

  it("still rejects a malformed listen request with the SDK's JSON-RPC error", async () => {
    const response = await modernRpc("subscriptions/listen", "listen:bad");
    const message = JSON.parse(await textWithin(response, 1000)) as { id: string; error: { code: number } };
    expect(message.id).toBe("listen:bad");
    expect(message.error.code).toBe(-32602);
  });
});
