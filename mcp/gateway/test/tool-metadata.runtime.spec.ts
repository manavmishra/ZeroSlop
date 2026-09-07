import { exports } from "cloudflare:workers";
import { describe, expect, it } from "vitest";

describe("MCP tool metadata in workerd", () => {
  it("declares persistent usage side effects without destructive or open-world access", async () => {
    const response = await exports.default.fetch("https://mcp.zero-slop.ai/mcp", {
      method: "POST",
      headers: {
        host: "mcp.zero-slop.ai",
        "content-type": "application/json",
        accept: "application/json, text/event-stream",
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
    });
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/event-stream");
    const data = (await response.text()).split("\n").find((line) => line.startsWith("data: "));
    expect(data).toBeDefined();
    const message = JSON.parse(data!.slice("data: ".length)) as {
      result: { tools: Array<{ name: string; annotations: Record<string, boolean> }> };
    };
    expect(message.result.tools).toHaveLength(1);
    expect(message.result.tools[0]?.name).toBe("deslop");
    expect(message.result.tools[0]?.annotations).toEqual({
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: false,
    });
  });
});
