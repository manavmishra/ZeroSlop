import type { PipelineResult } from "./types";
import type { McpRequestMeta } from "./telemetry";

const COUNTER_ORIGIN = "https://counter.internal";
const LEGACY_COUNTER_NAME = "global";
export const COUNTER_SHARD_COUNT = 32;
const COUNTER_SHARD_NAMES = Array.from(
  { length: COUNTER_SHARD_COUNT },
  (_, index) => `shard-${index.toString().padStart(2, "0")}`,
);
const READ_COUNTER_NAMES = [LEGACY_COUNTER_NAME, ...COUNTER_SHARD_NAMES];
const RETRY_DELAYS_MS = [0, 25, 100] as const;
const DEDUPLICATION_WINDOW_MS = 60 * 60 * 1000;
const encoder = new TextEncoder();
const REPORT_TOKEN_PROOF = encoder.encode("zero-slop-report-token-v1");

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

function isIsoTimestamp(value: string): boolean {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) && new Date(parsed).toISOString() === value;
}

export function isCounterSnapshot(value: unknown): value is CounterSnapshot {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<CounterSnapshot>;
  if (candidate.schema !== 1) return false;
  if (candidate.startedAt !== null && (typeof candidate.startedAt !== "string" || !isIsoTimestamp(candidate.startedAt))) {
    return false;
  }
  if (candidate.updatedAt !== null && (typeof candidate.updatedAt !== "string" || !isIsoTimestamp(candidate.updatedAt))) {
    return false;
  }
  if ((candidate.startedAt === null) !== (candidate.updatedAt === null)) return false;
  if (candidate.startedAt && candidate.updatedAt && candidate.startedAt > candidate.updatedAt) return false;
  if (!candidate.counters || typeof candidate.counters !== "object") return false;
  return COUNTER_METRICS.every((metric) => {
    const count = candidate.counters?.[metric];
    return Number.isSafeInteger(count) && Number(count) >= 0;
  });
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function fetchCounter(
  stub: DurableObjectStub,
  path: "/increment" | "/snapshot",
  init?: RequestInit,
): Promise<Response> {
  let lastStatus = 503;
  for (const delay of RETRY_DELAYS_MS) {
    if (delay) await sleep(delay);
    try {
      const response = await stub.fetch(`${COUNTER_ORIGIN}${path}`, init);
      lastStatus = response.status;
      if (response.ok || (response.status >= 400 && response.status < 500)) return response;
    } catch {
      lastStatus = 503;
    }
  }
  throw new Error(`counter returned ${lastStatus} after ${RETRY_DELAYS_MS.length} attempts`);
}

function writeCounterStub(env: Env): DurableObjectStub {
  const random = new Uint32Array(1);
  crypto.getRandomValues(random);
  const shard = COUNTER_SHARD_NAMES[(random[0] ?? 0) % COUNTER_SHARD_COUNT];
  if (!shard) throw new Error("counter shard unavailable");
  return env.MCP_COUNTER.getByName(shard);
}

export class McpCounter {
  private readonly storage: DurableObjectStorage;
  private readonly sql: SqlStorage;

  constructor(state: DurableObjectState) {
    this.storage = state.storage;
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
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS processed_events (
        id TEXT PRIMARY KEY,
        processed_at INTEGER NOT NULL
      )
    `);
    this.sql.exec(`
      CREATE INDEX IF NOT EXISTS processed_events_by_time
      ON processed_events(processed_at)
    `);
  }

  private increment(metrics: CounterMetric[], eventId: string): void {
    if (!metrics.length) return;
    const now = new Date().toISOString();
    const nowMs = Date.now();
    this.storage.transactionSync(() => {
      const duplicate = this.sql.exec<{ seen: number }>(
        "SELECT 1 AS seen FROM processed_events WHERE id = ? LIMIT 1",
        eventId,
      ).toArray().length > 0;
      if (duplicate) return;
      this.sql.exec(
        "INSERT INTO processed_events (id, processed_at) VALUES (?, ?)",
        eventId,
        nowMs,
      );
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
      this.sql.exec(
        "DELETE FROM processed_events WHERE processed_at < ?",
        nowMs - DEDUPLICATION_WINDOW_MS,
      );
    });
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
      const body = await request.json().catch(() => null) as { eventId?: unknown; metrics?: unknown } | null;
      if (
        !body
        || typeof body.eventId !== "string"
        || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(body.eventId)
        || !Array.isArray(body.metrics)
        || body.metrics.length === 0
        || body.metrics.length > COUNTER_METRICS.length
        || new Set(body.metrics).size !== body.metrics.length
        || body.metrics.some((metric) => !ALLOWED_METRICS.has(metric))
      ) {
        return Response.json({ error: "invalid_metrics" }, { status: 400 });
      }
      this.increment(body.metrics as CounterMetric[], body.eventId);
      return new Response(null, { status: 204 });
    }
    if (request.method === "GET" && url.pathname === "/snapshot") {
      return Response.json(this.snapshot());
    }
    return Response.json({ error: "not_found" }, { status: 404 });
  }
}

async function incrementCounters(env: Env, metrics: CounterMetric[]): Promise<void> {
  if (!metrics.length) return;
  const eventId = crypto.randomUUID();
  try {
    const response = await fetchCounter(writeCounterStub(env), "/increment", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ eventId, metrics }),
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
  const snapshots = await Promise.all(READ_COUNTER_NAMES.map(async (name) => {
    const response = await fetchCounter(env.MCP_COUNTER.getByName(name), "/snapshot");
    if (!response.ok) throw new Error(`counter returned ${response.status}`);
    const payload: unknown = await response.json();
    if (!isCounterSnapshot(payload)) throw new Error("counter returned an invalid snapshot");
    return payload;
  }));
  const counters = emptyCounters();
  let startedAt: string | null = null;
  let updatedAt: string | null = null;
  for (const snapshot of snapshots) {
    if (snapshot.startedAt && (!startedAt || snapshot.startedAt < startedAt)) startedAt = snapshot.startedAt;
    if (snapshot.updatedAt && (!updatedAt || snapshot.updatedAt > updatedAt)) updatedAt = snapshot.updatedAt;
    for (const metric of COUNTER_METRICS) {
      const total = counters[metric] + snapshot.counters[metric];
      if (!Number.isSafeInteger(total)) throw new Error("counter total exceeds the safe integer range");
      counters[metric] = total;
    }
  }
  return { schema: 1, startedAt, updatedAt, counters };
}

export async function reportTokenMatches(request: Request, expected: string | undefined): Promise<boolean> {
  if (!expected || expected.length < 32) return false;
  const header = request.headers.get("authorization") ?? "";
  const supplied = header.startsWith("Bearer ") ? header.slice(7) : "";
  try {
    // Web Crypto performs the comparison inside the cryptographic primitive.
    // This avoids handwritten character loops whose timing a JavaScript engine
    // is free to optimize differently.
    const expectedKey = await crypto.subtle.importKey(
      "raw", encoder.encode(expected), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
    );
    const suppliedKey = await crypto.subtle.importKey(
      "raw", encoder.encode(supplied || "invalid"), { name: "HMAC", hash: "SHA-256" }, false, ["verify"],
    );
    const proof = await crypto.subtle.sign("HMAC", expectedKey, REPORT_TOKEN_PROOF);
    return crypto.subtle.verify("HMAC", suppliedKey, proof, REPORT_TOKEN_PROOF);
  } catch {
    return false;
  }
}
