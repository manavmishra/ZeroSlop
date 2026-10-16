import { readBoundedJson } from "./bounded-json";
import { dailyBudgetClient, HostedBudgetError } from "./budget";
import { boundedOperation, checkCancelled, PipelineCancelledError, type PipelineControl } from "./cancellation";

// The website may try two providers. Leave bounded room for both deadlines,
// two budget checks, and the gateway-to-website response transit.
const REQUEST_TIMEOUT_MS = 65_000;
const MIN_ATTEMPT_MS = 750;
const MAX_EDITOR_RESPONSE_BYTES = 256 * 1024;
const MAX_EDITOR_OUTPUT_CHARS = 40_000;
const encoder = new TextEncoder();

export type ModelRole = "complete";
export type EditorFailure = "deadline" | "timeout" | "cancelled" | "configuration" | "unavailable" | "invalid_output" | "unchanged_output" | "transport";
class EditorInvalidResponseError extends Error {}

export type ModelReply = {
  text: string;
  rung: string;
  providerCalls: number;
};

function hex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function signedEditorHeaders(secret: string, body: string, now = Date.now()): Promise<Record<string, string>> {
  if (typeof secret !== "string" || secret.length < 32) throw new Error("editor_secret_unavailable");
  const timestamp = String(now);
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(`${timestamp}.${body}`));
  return {
    "x-zero-slop-timestamp": timestamp,
    "x-zero-slop-signature": hex(signature),
  };
}

type EditorResponse = {
  rewrite?: unknown;
  provider?: unknown;
  model?: unknown;
  stored?: unknown;
  providerCalls?: unknown;
};

type SafeProviderAttempt = {
  provider: string;
  outcome: string;
  failureStage?: string;
  httpStatus?: number;
};

// Endpoint diagnostics are untrusted. Copy only bounded enums and an observed
// numeric HTTP status, never messages, drafts, model names or other properties.
function safeProviderAttempts(value: unknown): SafeProviderAttempt[] {
  if (!value || typeof value !== "object" || !("providerAttempts" in value)) return [];
  const attempts = value.providerAttempts;
  if (!Array.isArray(attempts) || attempts.length > 2) return [];
  const outcomes = ["success", "timeout", "cancelled", "capacity", "invalid_output", "configuration", "unavailable"];
  const safe: SafeProviderAttempt[] = [];
  for (const attempt of attempts) {
    if (!attempt || typeof attempt !== "object" ||
        !["workers-ai", "openrouter"].includes(attempt.provider) || !outcomes.includes(attempt.outcome)) return [];
    const entry: SafeProviderAttempt = { provider: attempt.provider, outcome: attempt.outcome };
    if (attempt.outcome !== "success" && ["invoke", "fetch", "http", "body"].includes(attempt.failureStage)) {
      entry.failureStage = attempt.failureStage;
      if (["http", "body"].includes(attempt.failureStage) && typeof attempt.httpStatus === "number"
          && Number.isSafeInteger(attempt.httpStatus) && attempt.httpStatus >= 100 && attempt.httpStatus <= 599) {
        entry.httpStatus = attempt.httpStatus;
      }
    }
    safe.push(entry);
  }
  return safe;
}

function safeRungPart(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  if (!normalized || normalized.length > 120 || /[\u0000-\u001f\u007f]/.test(normalized)) return null;
  return normalized;
}

export function editorReply(value: unknown): ModelReply | null {
  if (!value || typeof value !== "object") return null;
  const data = value as EditorResponse;
  if (data.stored !== false) return null;
  if (typeof data.rewrite !== "string" || !data.rewrite.trim()) return null;
  const provider = safeRungPart(data.provider);
  const model = safeRungPart(data.model);
  if (!provider || !model) return null;
  const providerCalls = data.providerCalls === undefined ? 1 : data.providerCalls;
  if (!Number.isSafeInteger(providerCalls) || Number(providerCalls) < 1 || Number(providerCalls) > 2) return null;
  return { text: data.rewrite.trim(), rung: `${provider}:${model}`, providerCalls: Number(providerCalls) };
}

export function tooShort(source: string, output: string, _role: ModelRole = "complete"): boolean {
  const words = (value: string) => value.match(/\S+/g)?.length ?? 0;
  return words(output) < Math.min(18, Math.ceil(words(source) * 0.25));
}

export function tooLong(source: string, output: string, _role: ModelRole = "complete"): boolean {
  return output.length > Math.min(MAX_EDITOR_OUTPUT_CHARS, Math.max(1_000, source.length * 1.75));
}

export async function callRole(
  env: Env,
  role: ModelRole,
  source: string,
  diagnostics: Record<string, unknown>,
  deadline: number,
  clientAddress = "",
  control?: PipelineControl,
  onProviderCalls?: (count: 0 | 1 | 2) => void,
  onFailure?: (reason: EditorFailure) => void,
): Promise<ModelReply | null> {
  checkCancelled(control);
  const started = Date.now();
  const remaining = deadline - Date.now();
  if (remaining < MIN_ATTEMPT_MS) {
    onFailure?.("deadline");
    console.warn(JSON.stringify({ event: "editor_request_skipped", role, reason: "deadline" }));
    return null;
  }
  try {
    return await boundedOperation(async (signal) => {
      const body = JSON.stringify({
        role,
        text: source,
        diagnostics,
        genre: diagnostics.genre,
        noStore: true,
        budgetClient: await dailyBudgetClient(env.EDITOR_SHARED_SECRET, clientAddress),
        website: "",
      });
      const signatureHeaders = await signedEditorHeaders(env.EDITOR_SHARED_SECRET, body);
      checkCancelled(control);
      signal.throwIfAborted();
      if (control) control.editorRequested = true;
      const response = await fetch(env.EDITOR_ENDPOINT, {
        method: "POST",
        // workerd rejects redirect: "error" during Request construction.
        // Manual mode keeps signed drafts on this endpoint; !ok below rejects
        // every redirect without forwarding its body or signature elsewhere.
        redirect: "manual",
        signal,
        headers: {
          "cache-control": "no-store",
          "content-type": "application/json",
          ...signatureHeaders,
        },
        body,
      });
      if (!response.ok) {
        let failure: EditorFailure = "unavailable";
        let providerAttempts: SafeProviderAttempt[] = [];
        if (response.status === 429 || response.status === 503) {
          const errorBody = await readBoundedJson(response, 2048).catch(() => null);
          providerAttempts = safeProviderAttempts(errorBody);
          if (errorBody && typeof errorBody === "object" && "providerCalls" in errorBody) {
            const count = errorBody.providerCalls;
            if (count === 0 || count === 1 || count === 2) onProviderCalls?.(count);
          }
          const code = errorBody && typeof errorBody === "object" && "code" in errorBody ? errorBody.code : null;
          const endpointError = errorBody && typeof errorBody === "object" && "error" in errorBody ? errorBody.error : null;
          const endpointOutcome = errorBody && typeof errorBody === "object" && "editorOutcome" in errorBody ? errorBody.editorOutcome : null;
          if (endpointOutcome === "timeout") failure = "timeout";
          if (endpointOutcome === "invalid_output") failure = "invalid_output";
          if (endpointOutcome === "configuration") failure = "configuration";
          if (endpointOutcome === "cancelled") failure = "cancelled";
          if (endpointError === "editor_timeout") failure = "timeout";
          if (endpointError === "editor_invalid_output") failure = "invalid_output";
          if (endpointError === "editor_configuration") failure = "configuration";
          if (response.status === 429 && code === "usage_limit") {
            const retry = response.headers.get("retry-after") ?? "";
            if (!/^\d{1,5}$/.test(retry) || Number(retry) < 1 || Number(retry) > 86400) throw new HostedBudgetError("budget_unavailable");
            throw new HostedBudgetError("usage_limit", Number(retry));
          }
          if (code === "budget_unavailable") throw new HostedBudgetError("budget_unavailable");
        }
        onFailure?.(failure);
        console.warn(JSON.stringify({
          event: "editor_request_unavailable", role, status: response.status,
          reason: failure,
          providerAttempts,
          durationMs: Date.now() - started,
        }));
        return null;
      }
      let payload: unknown;
      try { payload = await readBoundedJson(response, MAX_EDITOR_RESPONSE_BYTES); }
      catch { throw new EditorInvalidResponseError(); }
      const reply = editorReply(payload);
      if (reply) onProviderCalls?.(reply.providerCalls as 1 | 2);
      if (!reply || tooShort(source, reply.text, role) || tooLong(source, reply.text, role) || reply.text === source) {
        const failure = reply?.text === source ? "unchanged_output" : "invalid_output";
        onFailure?.(failure);
        console.warn(JSON.stringify({
          event: "editor_request_rejected", role, reason: failure,
          durationMs: Date.now() - started,
        }));
        return null;
      }
      console.log(JSON.stringify({
        event: "editor_request_complete", role, providerCalls: reply.providerCalls,
        providerAttempts: safeProviderAttempts(payload), durationMs: Date.now() - started,
      }));
      return reply;
    }, Math.min(REQUEST_TIMEOUT_MS, remaining), control);
  } catch (error) {
    if (error instanceof HostedBudgetError || error instanceof PipelineCancelledError) throw error;
    const failure: EditorFailure = error instanceof Error && error.message === "editor_secret_unavailable"
      ? "configuration" : error instanceof EditorInvalidResponseError ? "invalid_output"
        : error instanceof Error && error.message === "upstream_deadline" ? "timeout" : "transport";
    onFailure?.(failure);
    console.warn(JSON.stringify({
      event: "editor_request_unavailable", role,
      reason: failure,
      durationMs: Date.now() - started,
    }));
    return null;
  }
}
