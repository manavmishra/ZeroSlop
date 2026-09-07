import { countCapacityReject, countPipelineFailure, countPipelineResult } from "./counter";
import { deslopInputSchema, deslopOutputSchema, MAX_REQUEST_BYTES, openApiDocument } from "./contract";
import { runPipeline } from "./pipeline";

const BODY_TIMEOUT_MS = 10_000;

class RequestError extends Error {
  constructor(readonly status: number, readonly code: string, message: string) { super(message); }
}

async function readDraft(request: Request): Promise<unknown> {
  const length = request.headers.get("content-length");
  if (length !== null) {
    const count = Number(length);
    if (!/^[0-9]+$/.test(length) || !Number.isSafeInteger(count)) {
      throw new RequestError(400, "invalid_length", "Content-Length must be a nonnegative integer.");
    }
    if (count > MAX_REQUEST_BYTES) throw new RequestError(413, "request_too_large", "The JSON request exceeds 128 KiB.");
  }
  if (!request.body) throw new RequestError(400, "invalid_json", "Send a JSON object containing text.");
  const reader = request.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let bytes = 0;
  let text = "";
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => reject(new RequestError(408, "body_timeout", "The JSON body must arrive within 10 seconds.")), BODY_TIMEOUT_MS);
  });
  try {
    while (true) {
      const part = await Promise.race([reader.read(), timeout]);
      if (part.done) break;
      bytes += part.value.byteLength;
      if (bytes > MAX_REQUEST_BYTES) throw new RequestError(413, "request_too_large", "The JSON request exceeds 128 KiB.");
      text += decoder.decode(part.value, { stream: true });
    }
    text += decoder.decode();
    return JSON.parse(text) as unknown;
  } catch (error) {
    // Cancellation is best-effort; awaiting a hostile source's cancel hook can hang.
    void reader.cancel().catch(() => undefined);
    if (error instanceof RequestError) throw error;
    throw new RequestError(400, "invalid_json", "Send a valid UTF-8 JSON object containing text.");
  } finally {
    clearTimeout(timer);
    reader.releaseLock();
  }
}

function problem(status: number, code: string, detail: string, requestId: string, extraHeaders: HeadersInit = {}) {
  const titles: Record<number, string> = {
    400: "Bad Request", 405: "Method Not Allowed", 408: "Request Timeout", 413: "Content Too Large",
    415: "Unsupported Media Type", 429: "Too Many Requests", 503: "Service Unavailable",
  };
  const headers = new Headers(extraHeaders);
  headers.set("content-type", "application/problem+json");
  headers.set("x-request-id", requestId);
  return Response.json({ type: "about:blank", title: titles[status] ?? "Request failed", status, detail, code, requestId }, { status, headers });
}

export async function handleRest(
  request: Request,
  env: Env,
  ctx: ExecutionContext,
  pipeline: typeof runPipeline = runPipeline,
): Promise<Response> {
  const requestId = crypto.randomUUID();
  if (new URL(request.url).pathname === "/openapi.json") {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return problem(405, "method_not_allowed", "Use GET to read the OpenAPI document.", requestId, { allow: "GET, HEAD" });
    }
    return request.method === "HEAD"
      ? new Response(null, { headers: { "content-type": "application/json" } })
      : Response.json(openApiDocument(env.SCORER_VERSION));
  }
  if (request.method !== "POST") return problem(405, "method_not_allowed", "Use POST with a JSON draft.", requestId, { allow: "POST" });
  const mediaType = request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
  if (mediaType !== "application/json" || (request.headers.has("content-encoding") && request.headers.get("content-encoding") !== "identity")) {
    return problem(415, "unsupported_media_type", "Send uncompressed application/json encoded as UTF-8.", requestId);
  }

  let body: unknown;
  try {
    body = await readDraft(request);
  } catch (error) {
    if (error instanceof RequestError) return problem(error.status, error.code, error.message, requestId);
    return problem(400, "invalid_request", "The draft could not be read.", requestId);
  }
  const parsed = deslopInputSchema.safeParse(body);
  if (!parsed.success) {
    return problem(400, "invalid_input", "Provide nonempty text up to 20,000 Unicode code points, an optional genre (general, social, email, research, professional), and an optional audience up to 200 Unicode code points.", requestId);
  }

  const started = Date.now();
  try {
    // The same binding AND key as MCP: adding a transport must not multiply capacity.
    const limited = await env.PIPELINE_LIMITER.limit({ key: "deslop-global" });
    if (!limited.success) {
      ctx.waitUntil(countCapacityReject(env));
      return problem(429, "capacity_limit", "Zero Slop is at its shared processing limit. Wait before retrying.", requestId, { "retry-after": "10" });
    }
    const { text, genre, audience } = parsed.data;
    const result = deslopOutputSchema.parse(await pipeline(env, { text, genre, ...(audience ? { audience } : {}) }));
    ctx.waitUntil(countPipelineResult(env, result));
    console.log(JSON.stringify({ event: "rest_deslop_complete", status: result.status, chars: parsed.data.text.length, durationMs: result.durationMs }));
    return Response.json(result, { headers: { "x-request-id": requestId } });
  } catch {
    ctx.waitUntil(countPipelineFailure(env));
    console.error(JSON.stringify({ event: "rest_deslop_failed", durationMs: Date.now() - started }));
    return problem(503, "service_unavailable", "Zero Slop could not produce a safely scored result. Your draft was not changed. Review before retrying.", requestId);
  }
}
