import { readBoundedJson } from "./bounded-json";

// The website endpoint owns a 24-second model deadline. This caller allows a
// small response margin while the whole MCP request remains bounded.
const REQUEST_TIMEOUT_MS = 28_000;
const MIN_ATTEMPT_MS = 750;
const MAX_EDITOR_RESPONSE_BYTES = 256 * 1024;
const MAX_EDITOR_OUTPUT_CHARS = 40_000;
const encoder = new TextEncoder();

export type ModelRole = "complete";

export type ModelReply = {
  text: string;
  rung: string;
};

function hex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function signedEditorHeaders(secret: string, body: string, now = Date.now()): Promise<Record<string, string>> {
  if (secret.length < 32) throw new Error("editor_secret_unavailable");
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
};

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
  return { text: data.rewrite.trim(), rung: `${provider}:${model}` };
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
): Promise<ModelReply | null> {
  const started = Date.now();
  const remaining = deadline - Date.now();
  if (remaining < MIN_ATTEMPT_MS) {
    console.warn(JSON.stringify({ event: "editor_request_skipped", role, reason: "deadline" }));
    return null;
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Math.min(REQUEST_TIMEOUT_MS, remaining));
  try {
    const body = JSON.stringify({
      role,
      text: source,
      diagnostics,
      genre: diagnostics.genre,
      noStore: true,
      website: "",
    });
    const signatureHeaders = await signedEditorHeaders(env.EDITOR_SHARED_SECRET, body);
    const response = await fetch(env.EDITOR_ENDPOINT, {
      method: "POST",
      redirect: "error",
      signal: controller.signal,
      headers: {
        "cache-control": "no-store",
        "content-type": "application/json",
        ...signatureHeaders,
      },
      body,
    });
    if (!response.ok) {
      console.warn(JSON.stringify({
        event: "editor_request_unavailable", role, status: response.status,
        durationMs: Date.now() - started,
      }));
      return null;
    }
    const payload = await readBoundedJson(response, MAX_EDITOR_RESPONSE_BYTES);
    const reply = editorReply(payload);
    if (!reply || tooShort(source, reply.text, role) || tooLong(source, reply.text, role) || reply.text === source) {
      console.warn(JSON.stringify({
        event: "editor_request_rejected", role, reason: "invalid_editor_output",
        durationMs: Date.now() - started,
      }));
      return null;
    }
    console.log(JSON.stringify({
      event: "editor_request_complete", role, rung: reply.rung, durationMs: Date.now() - started,
    }));
    return reply;
  } catch (error) {
    console.warn(JSON.stringify({
      event: "editor_request_unavailable", role,
      reason: error instanceof Error ? error.name : "unknown",
      durationMs: Date.now() - started,
    }));
    return null;
  } finally {
    clearTimeout(timer);
  }
}
