import { env } from "cloudflare:workers";
import { describe, expect, it, vi } from "vitest";
import worker from "../src/index";
import { dailyBudgetClient } from "../src/budget";

const report = {
  score: 90, band: "rewrite", words: 20, sentences: 2, flaggedPhrases: 3,
  sentenceVariety: "natural", readability: "clear", highWeightFlags: 3,
  punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
  shape: { measured: true, broetry: false, oneSentenceParagraphShare: 0, longestFragmentRun: 0 },
  register: { measured: true, words: 20, checked: 4, findings: [], twoPartContrasts: 0, announcements: 0 }, flags: [],
};
const input = { text: "It is important to note that Maya owns the report. Omar will review it by Friday.", genre: "professional" };

describe("budget errors through the real Worker transports", () => {
  for (const [code, status, retryAfterSeconds] of [["usage_limit", 429, 60], ["budget_unavailable", 503, null]] as const) {
    it(`preserves ${code} as REST status and an actionable MCP tool error`, async () => {
      const points: AnalyticsEngineDataPoint[] = [];
      const boundEnv = Object.assign({}, env, {
        SCORER: { async fetch() { return Response.json(report); } },
        MCP_ANALYTICS: { writeDataPoint(point: AnalyticsEngineDataPoint) { points.push(point); } },
      }) as Env;
      const pending: Promise<unknown>[] = [];
      const ctx = { waitUntil(promise: Promise<unknown>) { pending.push(promise); } } as ExecutionContext;
      const editor = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, options) => {
        expect(String(url)).toBe(env.EDITOR_ENDPOINT);
        const body = JSON.parse(String(options?.body));
        expect(body.budgetClient).toEqual(await dailyBudgetClient(env.EDITOR_SHARED_SECRET, "192.0.2.1"));
        return Response.json({ code }, { status, headers: retryAfterSeconds === null ? {} : { "retry-after": String(retryAfterSeconds) } });
      });
      try {
        const rest = await worker.fetch(new Request("https://mcp.zero-slop.ai/v1/deslop", {
          method: "POST", headers: { "content-type": "application/json", origin: "https://zero-slop.ai", "cf-connecting-ip": "192.0.2.1" }, body: JSON.stringify(input),
        }), boundEnv, ctx);
        expect(rest.status).toBe(status); expect(rest.headers.get("access-control-allow-origin")).toBe("https://zero-slop.ai");
        expect(rest.headers.get("cache-control")).toBe("no-store"); expect(rest.headers.get("retry-after")).toBe(retryAfterSeconds === null ? null : "60");
        expect(await rest.json()).toMatchObject({ type: "about:blank", code, status });
        const mcp = await worker.fetch(new Request("https://mcp.zero-slop.ai/mcp", {
          method: "POST", headers: { host: "mcp.zero-slop.ai", "content-type": "application/json", accept: "application/json, text/event-stream", "cf-connecting-ip": "192.0.2.1", "user-agent": "zero-slop-cli/2" },
          body: JSON.stringify({ jsonrpc: "2.0", id: 7, method: "tools/call", params: { name: "deslop", arguments: input } }),
        }), boundEnv, ctx);
        expect(mcp.status).toBe(200);
        const raw = await mcp.text();
        const event = raw.split("\n").find((line) => line.startsWith("data: "));
        const message = JSON.parse(event ? event.slice(6) : raw);
        expect(message.result.isError).toBe(true);
        expect(message.result.structuredContent).toBeUndefined();
        expect(message.result._meta["zero-slop/error"]).toEqual({ code, status, retryAfterSeconds });
        expect(message.result.content[0].text).not.toContain(input.text);
        if (retryAfterSeconds !== null) expect(message.result.content[0].text).toContain("60 seconds");
        expect(editor).toHaveBeenCalledTimes(2);
        for (const channel of ["rest", "cli"]) {
          const channelPoints = points.filter((point) => point.blobs?.[15] === channel);
          expect(channelPoints.filter((point) => point.blobs?.[1] === "request")).toHaveLength(1);
          const resultPoint = channelPoints.filter((point) => point.blobs?.[1] === "result");
          expect(resultPoint).toHaveLength(1);
          expect(resultPoint[0]?.blobs?.[4]).toBe(code);
          expect(resultPoint[0]?.doubles?.[17]).toBe(0);
        }
        expect(JSON.stringify(points)).not.toContain(input.text);
        expect(JSON.stringify(points)).not.toContain("192.0.2.1");
        await Promise.all(pending);
      } finally { editor.mockRestore(); }
    });
  }
});
