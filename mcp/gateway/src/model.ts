// The editor endpoint reserves up to 15 seconds for its binding-native
// backstop. Give that last rung time to answer; the separate 52-second
// pipeline deadline still caps the complete MCP call.
const ATTEMPT_TIMEOUT_MS = 16_000;
const MIN_ATTEMPT_MS = 750;
const encoder = new TextEncoder();

export type ModelRole =
  | "interpret"
  | "rewrite_strip"
  | "rewrite_warm"
  | "rewrite_surgical"
  | "copydesk"
  | "readaloud"
  | "verify"
  | "finalize";

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
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
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

export function editorReply(value: unknown): ModelReply | null {
  if (!value || typeof value !== "object") return null;
  const data = value as EditorResponse;
  if (data.stored !== false) return null;
  if (typeof data.rewrite !== "string" || !data.rewrite.trim()) return null;
  if (typeof data.provider !== "string" || !data.provider) return null;
  if (typeof data.model !== "string" || !data.model) return null;
  return { text: data.rewrite.trim(), rung: `${data.provider}:${data.model}` };
}

export function tooShort(source: string, output: string, role: ModelRole): boolean {
  if (role === "interpret" || role === "verify") return false;
  const words = (value: string) => value.match(/\S+/g)?.length ?? 0;
  const sourceWords = words(source);
  const outputWords = words(output);
  if (role === "rewrite_strip" || role === "rewrite_warm") {
    // Slop-heavy drafts can be mostly throat-clearing. Let the deterministic
    // fidelity gate judge a hard cut instead of rejecting it by length alone.
    // This still catches empty and obviously truncated model responses.
    return outputWords < Math.min(20, Math.max(3, sourceWords * 0.18));
  }
  return outputWords < Math.min(40, sourceWords * 0.45);
}

export async function callRole(
  env: Env,
  role: ModelRole,
  packet: string,
  expectedText: string,
  deadline: number,
  exclude: string[] = [],
  strictExclude = false,
): Promise<ModelReply | null> {
  const started = Date.now();
  const remaining = deadline - Date.now();
  if (remaining < MIN_ATTEMPT_MS) {
    console.warn(JSON.stringify({ event: "editor_role_skipped", role, reason: "deadline" }));
    return null;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Math.min(ATTEMPT_TIMEOUT_MS, remaining));
  try {
    const body = JSON.stringify({
      role,
      text: packet,
      exclude,
      strictExclude,
      noStore: true,
      website: "",
    });
    const signatureHeaders = await signedEditorHeaders(env.EDITOR_SHARED_SECRET, body);
    const response = await fetch(env.EDITOR_ENDPOINT, {
      method: "POST",
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
        event: "editor_role_unavailable",
        role,
        status: response.status,
        durationMs: Date.now() - started,
        excluded: exclude.length,
        strictExclude,
      }));
      return null;
    }
    const payload: unknown = await response.json();
    const reply = editorReply(payload);
    if (!reply) {
      const shape = payload && typeof payload === "object"
        ? Object.fromEntries(Object.entries(payload).slice(0, 12).map(([key, value]) => [key, typeof value]))
        : { value: typeof payload };
      console.warn(JSON.stringify({
        event: "editor_role_rejected",
        role,
        reason: "invalid_no_store_response",
        durationMs: Date.now() - started,
        shape,
      }));
      return null;
    }
    if (tooShort(expectedText, reply.text, role)) {
      console.warn(JSON.stringify({
        event: "editor_role_rejected",
        role,
        reason: "truncated",
        rung: reply.rung,
        sourceWords: expectedText.match(/\S+/g)?.length ?? 0,
        outputWords: reply.text.match(/\S+/g)?.length ?? 0,
        durationMs: Date.now() - started,
      }));
      return null;
    }
    console.log(JSON.stringify({
      event: "editor_role_complete",
      role,
      rung: reply.rung,
      durationMs: Date.now() - started,
      excluded: exclude.length,
      strictExclude,
    }));
    return reply;
  } catch (error) {
    console.warn(JSON.stringify({
      event: "editor_role_unavailable",
      role,
      reason: error instanceof Error ? error.name : "unknown",
      durationMs: Date.now() - started,
      excluded: exclude.length,
      strictExclude,
    }));
    return null;
  } finally {
    clearTimeout(timer);
  }
}
