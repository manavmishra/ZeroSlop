import { env } from "cloudflare:workers";
import { expect, it, vi } from "vitest";
import worker from "../src/index";
import { localRescue } from "../src/pipeline";

it("preserves only bounded editor diagnostics through real REST and MCP handlers in workerd", async () => {
  const source = "It is important to note that Maya owns the rollout for 25 teams.";
  const privateMarker = "private-provider-body-and-credential-marker";
  const report = {
    score: 90, band: "stock", words: 16, sentences: 1, flaggedPhrases: 1,
    sentenceVariety: "natural", readability: "clear", highWeightFlags: 1,
    punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
    shape: { measured: false, broetry: false, oneSentenceParagraphShare: null, longestFragmentRun: null },
    register: { measured: false, words: 16, checked: 0, findings: [], twoPartContrasts: 0, announcements: 0 }, flags: [],
  };
  const scorer = vi.fn(async (url: string, init?: RequestInit) => {
    if (new URL(url).pathname === "/report") return Response.json(report);
    expect(new URL(url).pathname).toBe("/rank");
    const payload = JSON.parse(String(init?.body));
    expect(payload.original).toBe(source);
    expect(payload.candidates).toEqual({ "local edit": localRescue(source) });
    return Response.json({
      name: "local edit", text: localRescue(source), preserved: true, invented: false, before: 90, after: 90,
      ranked: [{ name: "local edit", after: 90, preserved: true, invented: false }],
    });
  });
  const boundEnv = Object.assign({}, env, { SCORER: { fetch: scorer }, MCP_ANALYTICS: { writeDataPoint() {} } }) as Env;
  const outbound = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    expect(String(url)).toBe(env.EDITOR_ENDPOINT);
    return Response.json({
      error: privateMarker, editorOutcome: "unavailable", providerCalls: 2,
      providerAttempts: [
        { provider: "workers-ai", outcome: "invalid_output", outputStage: "source_preservation", text: privateMarker },
        { provider: "openrouter", outcome: "unavailable", failureStage: "http", httpStatus: 401, message: privateMarker },
      ],
      headers: privateMarker,
    }, { status: 503, headers: { "x-provider-detail": privateMarker } });
  });
  const pending: Promise<unknown>[] = [];
  const ctx = { waitUntil(promise: Promise<unknown>) { pending.push(promise); } } as ExecutionContext;
  try {
    for (const transport of ["rest", "mcp"]) {
      const response = await worker.fetch(new Request(`https://mcp.zero-slop.ai/${transport === "rest" ? "v1/deslop" : "mcp"}`, {
        method: "POST",
        headers: {
          host: "mcp.zero-slop.ai", "content-type": "application/json",
          accept: "application/json, text/event-stream", "cf-connecting-ip": "192.0.2.111",
        },
        body: JSON.stringify(transport === "rest" ? { text: source, genre: "social" } : {
          jsonrpc: "2.0", id: 12, method: "tools/call", params: { name: "deslop", arguments: { text: source, genre: "social" } },
        }),
      }), boundEnv, ctx);
      expect(response.status).toBe(200);
      expect(response.headers.get("cache-control")).toBe("no-store");
      const raw = await response.text();
      expect(raw).not.toContain(privateMarker);
      const event = raw.split("\n").find(line => line.startsWith("data: "));
      const message = JSON.parse(event ? event.slice(6) : raw);
      const result = transport === "rest" ? message : message.result.structuredContent;
      expect(result.editorDiagnostics).toEqual({
        endpointHttpStatus: 503,
        providerAttempts: [
          { provider: "workers-ai", outcome: "invalid_output", outputStage: "source_preservation" },
          { provider: "openrouter", outcome: "unavailable", failureStage: "http", httpStatus: 401 },
        ],
      });
      expect(result.text).toBe(localRescue(source));
      expect(result.status).toBe("rewritten_with_warnings");
      expect(result.factsPreserved).toBe(true);
      expect(result.passedFinalChecks).toBe(false);
      expect(result.modelRequests).toBe(2);
      expect(result.note).toContain("editor service was unavailable");
    }
    expect(outbound).toHaveBeenCalledTimes(2);
    await Promise.all(pending);
  } finally {
    outbound.mockRestore();
  }
});
