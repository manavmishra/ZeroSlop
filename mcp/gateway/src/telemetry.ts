import type { Genre, PipelineResult } from "./types";

const TELEMETRY_SCHEMA = "mcp-v1";
const UNKNOWN = "unknown";

export type McpRequestMeta = {
  method: string;
  tool: string;
  client: string;
  clientVersion: string;
  protocolVersion: string;
  country: string;
  colo: string;
  origin: string;
  isDeslopCall: boolean;
};

type JsonRpcMessage = {
  method?: unknown;
  params?: {
    name?: unknown;
    clientInfo?: { name?: unknown; version?: unknown };
    protocolVersion?: unknown;
  };
};

function boundedToken(value: unknown, fallback = UNKNOWN, max = 40): string {
  if (typeof value !== "string") return fallback;
  const normalized = value.trim().toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "");
  return normalized ? normalized.slice(0, max) : fallback;
}

function normalizeMethod(value: unknown): string {
  if (typeof value !== "string") return UNKNOWN;
  const known = new Set([
    "initialize",
    "notifications/initialized",
    "ping",
    "tools/list",
    "tools/call",
    "resources/list",
    "resources/read",
    "prompts/list",
    "prompts/get",
  ]);
  return known.has(value) ? value : "other";
}

export function classifyClient(name: unknown, userAgent: string | null): string {
  const source = `${typeof name === "string" ? name : ""} ${userAgent ?? ""}`.toLowerCase();
  if (/claude[ _-]?code/.test(source)) return "claude-code";
  if (/cowork/.test(source)) return "claude-cowork";
  if (/chatgpt/.test(source)) return "chatgpt";
  if (/codex/.test(source)) return "codex";
  if (/claude/.test(source)) return "claude";
  if (/cursor/.test(source)) return "cursor";
  if (/visual studio code|vscode/.test(source)) return "vscode";
  if (/insomnia/.test(source)) return "insomnia";
  if (/postman/.test(source)) return "postman";
  return UNKNOWN;
}

function majorVersion(value: unknown): string {
  if (typeof value !== "string") return UNKNOWN;
  const match = value.match(/(?:^|\D)(\d{1,4})(?:\D|$)/);
  return match?.[1] ?? UNKNOWN;
}

function protocolVersion(value: unknown): string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : UNKNOWN;
}

function requestOrigin(request: Request): string {
  const origin = request.headers.get("origin");
  if (!origin) return "none";
  try {
    const hostname = new URL(origin).hostname.toLowerCase();
    if (hostname === "zero-slop.ai" || hostname.endsWith(".zero-slop.ai")) return "zero-slop";
    if (hostname === "chatgpt.com" || hostname.endsWith(".chatgpt.com")) return "chatgpt";
    if (hostname === "claude.ai" || hostname.endsWith(".claude.ai")) return "claude";
    if (hostname === "localhost" || hostname === "127.0.0.1") return "local";
    return "other";
  } catch {
    return "invalid";
  }
}

function edgeLocation(request: Request): { country: string; colo: string } {
  const cf = (request as Request & { cf?: { country?: unknown; colo?: unknown } }).cf;
  const country = typeof cf?.country === "string" && /^[A-Za-z]{2}$/.test(cf.country)
    ? cf.country.toUpperCase()
    : UNKNOWN;
  const colo = typeof cf?.colo === "string" && /^[A-Za-z]{3}$/.test(cf.colo)
    ? cf.colo.toUpperCase()
    : UNKNOWN;
  return { country, colo };
}

export async function inspectMcpRequest(request: Request): Promise<McpRequestMeta> {
  let messages: JsonRpcMessage[] = [];
  if (request.method === "POST") {
    try {
      const body: unknown = await request.clone().json();
      const candidates = Array.isArray(body) ? body : [body];
      messages = candidates.filter((item): item is JsonRpcMessage => Boolean(item) && typeof item === "object");
    } catch {
      messages = [];
    }
  }

  const initialize = messages.find((message) => message.method === "initialize");
  const toolCall = messages.find((message) => message.method === "tools/call");
  const primary = toolCall ?? initialize ?? messages[0];
  const clientName = initialize?.params?.clientInfo?.name;
  const clientVersion = initialize?.params?.clientInfo?.version;
  const headerProtocol = request.headers.get("mcp-protocol-version");
  const location = edgeLocation(request);
  const tool = primary?.method === "tools/call" ? boundedToken(primary.params?.name) : "none";

  return {
    method: normalizeMethod(primary?.method),
    tool,
    client: classifyClient(clientName, request.headers.get("user-agent")),
    clientVersion: majorVersion(clientVersion),
    protocolVersion: protocolVersion(initialize?.params?.protocolVersion ?? headerProtocol),
    country: location.country,
    colo: location.colo,
    origin: requestOrigin(request),
    isDeslopCall: primary?.method === "tools/call" && tool === "deslop",
  };
}

type EventFields = {
  event: "request" | "result" | "capacity";
  outcome: string;
  genre?: Genre;
  beforeBand?: string;
  afterBand?: string;
  scorerVersion?: string;
  durationMs?: number;
  inputChars?: number;
  inputWords?: number;
  outputChars?: number;
  outputWords?: number;
  beforeScore?: number;
  afterScore?: number;
  scoreChange?: number;
  beforeFlags?: number;
  afterFlags?: number;
  rolesCompleted?: number;
  rounds?: number;
  independentChecks?: number;
  factsPreserved?: boolean;
  finalChecks?: boolean;
  httpStatus?: number;
};

export function telemetryPoint(meta: McpRequestMeta, fields: EventFields): AnalyticsEngineDataPoint {
  const safeNumber = (value: number | undefined): number => Number.isFinite(value) ? value ?? 0 : 0;
  const index = `${fields.event}:${meta.client}`;
  return {
    indexes: [index],
    blobs: [
      TELEMETRY_SCHEMA,
      fields.event,
      meta.method,
      meta.tool,
      boundedToken(fields.outcome),
      meta.client,
      meta.clientVersion,
      meta.protocolVersion,
      fields.genre ?? "none",
      boundedToken(fields.beforeBand, "none"),
      boundedToken(fields.afterBand, "none"),
      boundedToken(fields.scorerVersion, "none"),
      meta.country,
      meta.colo,
      meta.origin,
    ],
    doubles: [
      1,
      safeNumber(fields.durationMs),
      safeNumber(fields.inputChars),
      safeNumber(fields.inputWords),
      safeNumber(fields.outputChars),
      safeNumber(fields.outputWords),
      safeNumber(fields.beforeScore),
      safeNumber(fields.afterScore),
      safeNumber(fields.scoreChange),
      safeNumber(fields.beforeFlags),
      safeNumber(fields.afterFlags),
      safeNumber(fields.rolesCompleted),
      safeNumber(fields.rounds),
      safeNumber(fields.independentChecks),
      fields.factsPreserved ? 1 : 0,
      fields.finalChecks ? 1 : 0,
      safeNumber(fields.httpStatus),
    ],
  };
}

function write(env: Env, meta: McpRequestMeta, fields: EventFields): void {
  try {
    env.MCP_ANALYTICS?.writeDataPoint(telemetryPoint(meta, fields));
  } catch (error) {
    console.warn(JSON.stringify({
      event: "mcp_telemetry_write_failed",
      message: error instanceof Error ? error.message.slice(0, 80) : "unknown",
    }));
  }
}

export function trackMcpRequest(env: Env, meta: McpRequestMeta, status: number, durationMs: number): void {
  write(env, meta, {
    event: "request",
    outcome: status < 400 ? "ok" : "error",
    httpStatus: status,
    durationMs,
  });
}

export function trackCapacityLimit(env: Env, meta: McpRequestMeta): void {
  write(env, meta, { event: "capacity", outcome: "limited", httpStatus: 429 });
}

export function trackPipelineResult(
  env: Env,
  meta: McpRequestMeta,
  genre: Genre,
  inputChars: number,
  result: PipelineResult,
): void {
  write(env, meta, {
    event: "result",
    outcome: result.status,
    genre,
    beforeBand: result.before.band,
    afterBand: result.after.band,
    scorerVersion: result.scorerVersion,
    durationMs: result.durationMs,
    inputChars,
    inputWords: result.before.words,
    outputChars: result.text.length,
    outputWords: result.after.words,
    beforeScore: result.before.score,
    afterScore: result.after.score,
    scoreChange: result.scoreChange,
    beforeFlags: result.before.flaggedPhrases,
    afterFlags: result.after.flaggedPhrases,
    rolesCompleted: result.rolesCompleted,
    rounds: result.finishingRounds,
    independentChecks: result.independentModelChecks,
    factsPreserved: result.factsPreserved,
    finalChecks: result.passedFinalChecks,
    httpStatus: 200,
  });
}

export function trackPipelineFailure(
  env: Env,
  meta: McpRequestMeta,
  genre: Genre,
  inputChars: number,
  durationMs: number,
): void {
  write(env, meta, {
    event: "result",
    outcome: "failed",
    genre,
    inputChars,
    durationMs,
    httpStatus: 500,
  });
}
