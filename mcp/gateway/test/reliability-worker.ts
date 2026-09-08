// Maintainer-only fixture. Never deploy this entrypoint: its local control
// routes and fake bindings are intentionally not part of the production Worker.
import { DurableObject, WorkerEntrypoint } from "cloudflare:workers";
import gateway, { McpCounter } from "../src/index";
import { onRequestPost } from "reliability:pages-editor";

// The production fetch-based class predates DO RPC. This test-only adapter
// enables Miniflare's storage inspector without changing production storage.
export class ReliabilityBudget extends DurableObject {
  inner: McpCounter;
  constructor(ctx: DurableObjectState, env: Env) { super(ctx, env); this.inner = new McpCounter(ctx, env); }
  fetch(request: Request) { return this.inner.fetch(request); }
  alarm() { return this.inner.alarm(); }
}
const clean = "Maya owns the report. Omar will read it by Friday.";
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const phases = new Map<string, ReturnType<typeof newStats>>();
let config: Record<string, any> = { phase: "initial" };
function newStats() {
  return { requests: 0, completed: 0, active: 0, aborts: 0, editorRequests: 0, editorAborts: 0,
    scorerCalls: 0, scorerPending: 0, reserveAttempts: 0, reservePending: 0, grants: 0,
    reservedNeurons: 0, modelStarts: 0, modelPending: 0, modelFinishes: 0, modelAborts: 0,
    outboundBlocked: 0, results: [] as Array<{ status: number; modelRequests: number }> };
}
function stats(phase = config.phase) {
  if (!phases.has(phase)) phases.set(phase, newStats());
  return phases.get(phase)!;
}
function report(text: string) {
  const score = text.startsWith("It is important") ? 80 : 8;
  return { score, band: "synthetic", words: 20, sentences: 2, flaggedPhrases: score > 25 ? 1 : 0,
    sentenceVariety: "natural", readability: "clear", punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
    highWeightFlags: score > 25 ? 1 : 0,
    shape: { measured: false, broetry: false, oneSentenceParagraphShare: null, longestFragmentRun: null },
    register: { measured: false, words: 20, checked: 0, findings: [], twoPartContrasts: 0, announcements: 0 }, flags: [] };
}
function retained<T>(ctx: ExecutionContext, operation: Promise<T>): Promise<T> {
  ctx.waitUntil(operation.then(() => undefined, () => undefined));
  return operation;
}
function scopedEnv(env: any, cfg: typeof config, s: ReturnType<typeof newStats>, ctx: ExecutionContext) {
  return { ...env,
    PIPELINE_LIMITER: { async limit() { return { success: cfg.capacity !== false }; } },
    SCORER: { fetch(url: string, init?: RequestInit) { return retained(ctx, (async () => {
      s.scorerCalls++; s.scorerPending++;
      try {
        await sleep(cfg.scorerDelay ?? 2); // Deliberately ignores abort.
        if (cfg.scorerFailure) return new Response("synthetic", { status: 503 });
        if (cfg.scorerMalformed) return Response.json({ score: "invalid" });
        const path = new URL(url).pathname;
        if (path === "/health") return Response.json({ ok: true, scorerVersion: env.SCORER_VERSION });
        const body = JSON.parse(String(init?.body));
        if (path === "/report") return Response.json(report(body.text));
        if (path === "/rank") {
          const [name, text] = Object.entries(body.candidates)[0] as [string, string];
          return Response.json({ name, text, preserved: true, invented: false, before: 80, after: 8,
            ranked: Object.keys(body.candidates).map((name) => ({ name, preserved: true, invented: false, after: 8 })) });
        }
        throw new Error("unexpected_scorer_path");
      } finally { s.scorerPending--; }
    })()); } },
    MCP_ANALYTICS: { writeDataPoint(point: any) {
      if (point.blobs[1] === "result") s.results.push({ status: point.doubles[16], modelRequests: point.doubles[17] });
    } },
  };
}
async function editor(request: Request, env: any, ctx: ExecutionContext) {
  const cfg = { ...config }; const s = stats(cfg.phase);
  s.editorRequests++;
  request.signal.addEventListener("abort", () => { s.editorAborts++; }, { once: true });
  const bindings = scopedEnv(env, cfg, s, ctx);
  bindings.MCP_EDITOR_SHARED_SECRET = env.EDITOR_SHARED_SECRET;
  bindings.EDITOR_BUDGET = cfg.missingBudget ? undefined : { getByName(name: string) {
    return { fetch(url: string, init: RequestInit) { return retained(ctx, (async () => {
      s.reserveAttempts++; s.reservePending++;
      try {
        await sleep(cfg.reserveDelay ?? 0); // Deliberately ignores abort.
        if (cfg.reserveFailure) throw new Error("synthetic_budget_unavailable");
        if (cfg.reserveMalformed) return Response.json({ allowed: true });
        const response = await env.MCP_COUNTER.getByName(`${cfg.phase}/${name}`).fetch(url, init);
        const grant = await response.clone().json();
        if (grant.allowed) { s.grants++; s.reservedNeurons += JSON.parse(String(init.body)).neurons; }
        return response;
      } finally { s.reservePending--; }
    })()); } };
  } };
  bindings.AI = { run(_model: string, _input: unknown, options: { signal: AbortSignal }) { return retained(ctx, (async () => {
    s.modelStarts++; s.modelPending++;
    options.signal.addEventListener("abort", () => { s.modelAborts++; }, { once: true });
    try {
      await sleep(cfg.modelDelay ?? 5); // No inference; intentionally ignores abort.
      if (cfg.modelFailure) throw new Error("synthetic_model_failure");
      return { response: clean };
    } finally { s.modelPending--; s.modelFinishes++; }
  })()); } };
  const operation = onRequestPost({ request, env: bindings });
  // Keep the test observable after a real socket disconnect. Production does
  // not keep inference alive this way; no fake work survives fixture teardown.
  ctx.waitUntil(operation.then(() => undefined, () => undefined));
  return operation;
}

export class Editor extends WorkerEntrypoint {
  async fetch(request: Request) {
    if (new URL(request.url).hostname !== "editor.invalid") {
      stats().outboundBlocked++;
      return new Response("outbound_network_forbidden", { status: 502 });
    }
    return editor(request, this.env, this.ctx);
  }
}

export default {
  async fetch(request: Request, env: any, ctx: ExecutionContext) {
    const path = new URL(request.url).pathname;
    if (path === "/__control" && request.method === "POST") {
      config = await request.json(); stats(); return Response.json({ ok: true });
    }
    if (path === "/__stats") return Response.json(stats(new URL(request.url).searchParams.get("phase") ?? config.phase));
    const cfg = { ...config }; const s = stats(cfg.phase);
    s.requests++; s.active++;
    request.signal.addEventListener("abort", () => { s.aborts++; }, { once: true });
    const operation = (path === "/api/demo-rewrite" ? editor(request, env, ctx)
      : gateway.fetch(request, scopedEnv(env, cfg, s, ctx), ctx))
      .finally(() => { s.active--; s.completed++; });
    ctx.waitUntil(operation.then(() => undefined, () => undefined));
    return operation;
  },
};
