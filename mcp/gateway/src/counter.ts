import type { PipelineResult } from "./types";
import type { McpRequestMeta } from "./telemetry";

const COUNTER_ORIGIN = "https://counter.internal";
const COUNTER_NAME = "global";

export const COUNTER_METRICS = [
  "client_initializations",
  "mcp_tool_calls",
  "deslop_results",
  "messages_deslopped",
  "already_clear",
  "safe_responses",
  "review_warnings",
  "fully_verified",
  "unchanged_responses",
  "pipeline_failures",
  "capacity_rejects",
  "request_errors",
] as const;

export type CounterMetric = typeof COUNTER_METRICS[number];

export type CounterSnapshot = {
  schema: 1;
  startedAt: string | null;
  updatedAt: string | null;
  counters: Record<CounterMetric, number>;
};

const ALLOWED_METRICS = new Set<string>(COUNTER_METRICS);

function emptyCounters(): Record<CounterMetric, number> {
  return Object.fromEntries(COUNTER_METRICS.map((metric) => [metric, 0])) as Record<CounterMetric, number>;
}

export class McpCounter {
  private readonly sql: SqlStorage;

  constructor(state: DurableObjectState) {
    this.sql = state.storage.sql;
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS counters (
        name TEXT PRIMARY KEY,
        value INTEGER NOT NULL CHECK (value >= 0)
      )
    `);
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS metadata (
        name TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    `);
  }

  private increment(metrics: CounterMetric[]): void {
    if (!metrics.length) return;
    const now = new Date().toISOString();
    this.sql.exec(
      "INSERT OR IGNORE INTO metadata (name, value) VALUES ('started_at', ?)",
      now,
    );
    this.sql.exec(
      "INSERT INTO metadata (name, value) VALUES ('updated_at', ?) "
        + "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
      now,
    );
    for (const metric of metrics) {
      this.sql.exec(
        "INSERT INTO counters (name, value) VALUES (?, 1) "
          + "ON CONFLICT(name) DO UPDATE SET value = counters.value + 1",
        metric,
      );
    }
  }

  private snapshot(): CounterSnapshot {
    const counters = emptyCounters();
    for (const row of this.sql.exec<{ name: string; value: number }>(
      "SELECT name, value FROM counters",
    ).toArray()) {
      if (ALLOWED_METRICS.has(row.name)) counters[row.name as CounterMetric] = Number(row.value);
    }
    const metadata = new Map(
      this.sql.exec<{ name: string; value: string }>("SELECT name, value FROM metadata")
        .toArray()
        .map((row) => [row.name, row.value]),
    );
    return {
      schema: 1,
      startedAt: metadata.get("started_at") ?? null,
      updatedAt: metadata.get("updated_at") ?? null,
      counters,
    };
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/increment") {
      const body = await request.json().catch(() => null) as { metrics?: unknown } | null;
      if (
        !body
        || !Array.isArray(body.metrics)
        || body.metrics.length > COUNTER_METRICS.length
        || new Set(body.metrics).size !== body.metrics.length
        || body.metrics.some((metric) => !ALLOWED_METRICS.has(metric))
      ) {
        return Response.json({ error: "invalid_metrics" }, { status: 400 });
      }
      this.increment(body.metrics as CounterMetric[]);
      return new Response(null, { status: 204 });
    }
    if (request.method === "GET" && url.pathname === "/snapshot") {
      return Response.json(this.snapshot());
    }
    return Response.json({ error: "not_found" }, { status: 404 });
  }
}

function counterStub(env: Env): DurableObjectStub | null {
  return env.MCP_COUNTER?.getByName(COUNTER_NAME) ?? null;
}

async function incrementCounters(env: Env, metrics: CounterMetric[]): Promise<void> {
  if (!metrics.length) return;
  try {
    const stub = counterStub(env);
    if (!stub) return;
    const response = await stub.fetch(`${COUNTER_ORIGIN}/increment`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ metrics }),
    });
    if (!response.ok) throw new Error(`counter returned ${response.status}`);
  } catch (error) {
    console.warn(JSON.stringify({
      event: "mcp_counter_write_failed",
      message: error instanceof Error ? error.message.slice(0, 80) : "unknown",
    }));
  }
}

export async function countMcpRequest(
  env: Env,
  meta: McpRequestMeta,
  status: number,
): Promise<void> {
  const metrics: CounterMetric[] = [];
  if (meta.method === "initialize" && status < 400) metrics.push("client_initializations");
  if (meta.method === "tools/call") metrics.push("mcp_tool_calls");
  if (status >= 400) metrics.push("request_errors");
  await incrementCounters(env, metrics);
}

export async function countCapacityReject(env: Env): Promise<void> {
  await incrementCounters(env, ["capacity_rejects"]);
}

export async function countPipelineResult(env: Env, result: PipelineResult): Promise<void> {
  const metrics: CounterMetric[] = ["deslop_results", "safe_responses"];
  if (result.status === "rewritten" || result.status === "rewritten_with_warnings") {
    metrics.push("messages_deslopped");
  }
  if (result.status === "already_clear") metrics.push("already_clear");
  if (result.status === "rewritten_with_warnings") metrics.push("review_warnings");
  if (result.passedFinalChecks) metrics.push("fully_verified");
  if (result.status.startsWith("unchanged_")) metrics.push("unchanged_responses");
  await incrementCounters(env, metrics);
}

export async function countPipelineFailure(env: Env): Promise<void> {
  await incrementCounters(env, ["pipeline_failures"]);
}

export async function readCounterSnapshot(env: Env): Promise<CounterSnapshot> {
  const stub = counterStub(env);
  if (!stub) throw new Error("counter binding is unavailable");
  const response = await stub.fetch(`${COUNTER_ORIGIN}/snapshot`);
  if (!response.ok) throw new Error(`counter returned ${response.status}`);
  return response.json<CounterSnapshot>();
}

export function reportTokenMatches(request: Request, expected: string | undefined): boolean {
  if (!expected || expected.length < 32) return false;
  const header = request.headers.get("authorization") ?? "";
  const supplied = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (supplied.length !== expected.length) return false;
  let difference = 0;
  for (let index = 0; index < expected.length; index += 1) {
    difference |= expected.charCodeAt(index) ^ supplied.charCodeAt(index);
  }
  return difference === 0;
}
