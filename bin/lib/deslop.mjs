// Shared hosted-MCP client. No filesystem, process, model or local-scoring work.
export const MCP_ENDPOINT = "https://mcp.zero-slop.ai/mcp";
export const GENRES = Object.freeze(["general", "social", "email", "research", "professional"]);
export const RESULT_STATUSES = Object.freeze([
  "rewritten", "rewritten_with_warnings", "already_clear",
  "unchanged_no_better_version", "unchanged_verification_failed",
  "unchanged_service_unavailable",
]);
const PROTOCOLS = ["2025-11-25", "2025-06-18"];
const MAX_REQUEST_BYTES = 128 * 1024;
const MAX_RESPONSE_BYTES = 8 * 1024 * 1024;
const encoder = new TextEncoder();
// Zod's MCP string limits count Unicode code points, not UTF-16 units.
// Avoid allocating a character array, and stop as soon as the bound is crossed.
const withinLength = (value, maximum) => {
  if (value.length <= maximum) return true;
  let count = 0;
  for (const _character of value) if (++count > maximum) return false;
  return true;
};

export class DeslopError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "DeslopError";
    this.code = code;
    Object.assign(this, details);
  }
}

export function validateInput(input) {
  if (!input || typeof input.text !== "string") {
    throw new DeslopError("invalid_input", "Provide one UTF-8 draft as text.");
  }
  const text = input.text.trim();
  const genre = input.genre === undefined ? "general" : input.genre;
  if (!text || !withinLength(text, 20_000)) {
    throw new DeslopError("invalid_input", "The draft must contain 1–20,000 Unicode code points after trimming.");
  }
  if (!GENRES.includes(genre)) {
    throw new DeslopError("invalid_input", `Genre must be one of: ${GENRES.join(", ")}.`);
  }
  if (input.audience !== undefined && (typeof input.audience !== "string" || !withinLength(input.audience.trim(), 200))) {
    throw new DeslopError("invalid_input", "Audience must be at most 200 Unicode code points.");
  }
  // Never forward filenames, private preferences or other caller properties.
  return { text, genre, ...(input.audience?.trim() ? { audience: input.audience.trim() } : {}) };
}

const object = (value) => Boolean(value) && typeof value === "object" && !Array.isArray(value);
const number = (value, min, max = Infinity) => typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;
const integer = (value) => Number.isSafeInteger(value) && value >= 0;
const string = (value, max = Infinity) => typeof value === "string" && withinLength(value, max);
const array = (value, max, check) => Array.isArray(value) && value.length <= max && value.every(check);

function validReport(value) {
  return object(value) && number(value.score, 0, 100) && string(value.band, 80) && value.band.length > 0
    && [value.words, value.sentences, value.flaggedPhrases, value.highWeightFlags].every(integer)
    && ["natural", "too even"].includes(value.sentenceVariety) && ["clear", "needs work"].includes(value.readability)
    && object(value.punctuation) && [value.punctuation.dashes, value.punctuation.emoji, value.punctuation.hashtags].every(integer)
    && object(value.shape) && typeof value.shape.measured === "boolean" && typeof value.shape.broetry === "boolean"
    && (value.shape.oneSentenceParagraphShare === null || number(value.shape.oneSentenceParagraphShare, 0, 1))
    && (value.shape.longestFragmentRun === null || integer(value.shape.longestFragmentRun))
    && object(value.register) && typeof value.register.measured === "boolean"
    && [value.register.words, value.register.checked, value.register.twoPartContrasts, value.register.announcements].every(integer)
    && array(value.register.findings, 1_000, (finding) => object(finding) && string(finding.name, 160)
      && [finding.rate, finding.budget].every((item) => number(item, 0)) && integer(finding.found) && string(finding.quote, 1_000))
    && array(value.flags, 5_000, (flag) => object(flag) && string(flag.phrase, 1_000)
      && number(flag.strength, 0) && string(flag.issue, 2_000) && string(flag.direction, 2_000));
}

export function validateResult(result) {
  if (!object(result) || !string(result.text) || !RESULT_STATUSES.includes(result.status)
    || !validReport(result.before) || !validReport(result.after) || !number(result.scoreChange, -100, 100)
    || typeof result.factsPreserved !== "boolean" || typeof result.passedFinalChecks !== "boolean"
    || ![result.independentModelChecks, result.modelRequests, result.rolesCompleted, result.finishingRounds, result.durationMs].every(integer)
    || result.modelRequests > 1 || !string(result.scorerVersion) || !string(result.note)) {
    throw new DeslopError("invalid_response", "The MCP service returned an invalid structured result.");
  }
  // Return the original object, including additive fields; never rewrite its status.
  return result;
}

export function isApprovedResult(result) {
  try { validateResult(result); } catch { return false; }
  return result?.factsPreserved === true && (
    (result.status === "rewritten" && result.passedFinalChecks === true)
    || (result.status === "already_clear" && result.modelRequests === 0
      && result.scoreChange === 0 && result.before?.score === result.after?.score)
  );
}

function messageFromJson(raw, id) {
  let message;
  try { message = JSON.parse(raw); } catch {
    throw new DeslopError("invalid_response", "The MCP service returned malformed JSON.");
  }
  if (!object(message) || message.jsonrpc !== "2.0") {
    throw new DeslopError("invalid_response", "The MCP service returned an invalid protocol message.");
  }
  if (message.id !== id) return null;
  if (message.error !== undefined) {
    const rpcCode = Number.isSafeInteger(message.error?.code) ? message.error.code : undefined;
    throw new DeslopError("protocol_error", "The MCP service rejected the request.", { rpcCode });
  }
  if (!object(message.result)) {
    throw new DeslopError("invalid_response", "The MCP service returned no result.");
  }
  return message.result;
}

async function readReply(response, id, signal) {
  const type = response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase();
  if (!["application/json", "text/event-stream"].includes(type) || !response.body) {
    void response.body?.cancel().catch(() => {});
    throw new DeslopError("invalid_response", "The MCP service returned an unsupported response type.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let size = 0;
  let buffer = "";
  const stop = () => { void reader.cancel().catch(() => {}); };
  signal.addEventListener("abort", stop, { once: true });
  try {
    while (true) {
      signal.throwIfAborted();
      const { value, done } = await reader.read();
      signal.throwIfAborted();
      if (value) {
        size += value.byteLength;
        if (size > MAX_RESPONSE_BYTES) throw new DeslopError("invalid_response", "The MCP response exceeded the size limit.");
      }
      buffer += decoder.decode(value, { stream: !done });
      if (type === "text/event-stream") {
        let boundary;
        while ((boundary = /\r\n\r\n|\n\n|\r\r/.exec(buffer))) {
          const event = buffer.slice(0, boundary.index);
          buffer = buffer.slice(boundary.index + boundary[0].length);
          const data = event.split(/\r\n|\n|\r/).filter((line) => line.startsWith("data:"))
            .map((line) => line.slice(5).replace(/^ /, "")).join("\n");
          if (!data) continue;
          const reply = messageFromJson(data, id);
          if (reply) return reply;
        }
      } else if (done) {
        const reply = messageFromJson(buffer, id);
        if (reply) return reply;
      }
      if (done) throw new DeslopError("invalid_response", "The MCP response ended before the matching result arrived.");
    }
  } catch (error) {
    if (signal.aborted) throw signal.reason;
    if (error instanceof DeslopError) throw error;
    throw new DeslopError("invalid_response", "The MCP response could not be read.");
  } finally {
    signal.removeEventListener("abort", stop);
    stop();
    reader.releaseLock();
  }
}

/** Call the existing hosted pipeline once. Cancellation cannot guarantee server work stops. */
export async function deslop(input, options = {}) {
  const args = validateInput(input);
  const timeoutMs = options.timeoutMs ?? 75_000;
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 300_000) {
    throw new DeslopError("invalid_input", "Timeout must be between 1 and 300,000 milliseconds.");
  }
  const clientName = options.clientName ?? "zero-slop";
  const clientVersion = options.clientVersion ?? "unknown";
  if (!/^[a-zA-Z0-9._-]{1,64}$/.test(clientName) || !/^[a-zA-Z0-9.+_-]{1,64}$/.test(clientVersion)) {
    throw new DeslopError("invalid_input", "Client name and version must be bounded application metadata.");
  }
  const toolBody = { jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "deslop", arguments: args } };
  if (encoder.encode(JSON.stringify(toolBody)).byteLength > MAX_REQUEST_BYTES) {
    throw new DeslopError("invalid_input", "The encoded MCP request exceeds 128 KiB.");
  }
  const controller = new AbortController();
  const cancel = () => controller.abort(new DeslopError("cancelled", "Cancelled locally; hosted processing may still finish."));
  if (options.signal?.aborted) cancel();
  else options.signal?.addEventListener("abort", cancel, { once: true });
  const timer = setTimeout(() => controller.abort(new DeslopError("timeout", "The hosted request timed out; its outcome is unknown. No retry was sent.")), timeoutMs);
  let protocolVersion = PROTOCOLS[0];
  let session;
  let toolPending = false;
  const headers = () => ({
    "content-type": "application/json", accept: "application/json, text/event-stream",
    "cache-control": "no-store", "mcp-protocol-version": protocolVersion,
    ...(session ? { "mcp-session-id": session } : {}),
  });
  // A dropped HTTP connection is not an MCP cancellation notification. Request it
  // separately, without replaying the tool, but bound this best-effort cleanup.
  const notifyCancellation = () => {
    if (!toolPending) return;
    const cleanup = new AbortController();
    const cleanupTimer = setTimeout(() => cleanup.abort(), 250);
    void fetch(MCP_ENDPOINT, {
      method: "POST", redirect: "manual", signal: cleanup.signal, headers: headers(),
      body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/cancelled", params: { requestId: 2, reason: "Client cancelled" } }),
    }).then((response) => response.body?.cancel()).catch(() => {}).finally(() => clearTimeout(cleanupTimer));
  };
  controller.signal.addEventListener("abort", notifyCancellation, { once: true });
  async function rpc(body, notification = false) {
    controller.signal.throwIfAborted();
    const response = await fetch(MCP_ENDPOINT, {
      method: "POST", redirect: "manual", signal: controller.signal, headers: headers(), body: JSON.stringify(body),
    });
    controller.signal.throwIfAborted();
    if (!response.ok) {
      void response.body?.cancel().catch(() => {});
      const retry = response.headers.get("retry-after");
      const retryAfterSeconds = retry && /^\d{1,5}$/.test(retry) ? Number(retry) : undefined;
      throw new DeslopError("http_error", `The MCP service returned HTTP ${response.status}. No retry was sent.`, {
        httpStatus: response.status, ...(retryAfterSeconds !== undefined ? { retryAfterSeconds } : {}),
      });
    }
    if (notification) {
      void response.body?.cancel().catch(() => {});
      return;
    }
    if (body.method === "initialize") {
      session = response.headers.get("mcp-session-id");
      if (session && !/^[\x21-\x7e]{1,512}$/.test(session)) {
        void response.body?.cancel().catch(() => {});
        throw new DeslopError("invalid_response", "The MCP service returned an invalid session identifier.");
      }
    }
    return readReply(response, body.id, controller.signal);
  }
  try {
    const initialized = await rpc({ jsonrpc: "2.0", id: 1, method: "initialize", params: {
      protocolVersion, capabilities: {}, clientInfo: { name: clientName, version: clientVersion },
    } });
    if (!PROTOCOLS.includes(initialized.protocolVersion)) {
      throw new DeslopError("unsupported_protocol", "The MCP service negotiated an unsupported protocol version.");
    }
    protocolVersion = initialized.protocolVersion;
    await rpc({ jsonrpc: "2.0", method: "notifications/initialized" }, true);
    toolPending = true;
    const reply = await rpc(toolBody);
    toolPending = false;
    if (reply.isError !== undefined && typeof reply.isError !== "boolean") {
      throw new DeslopError("invalid_response", "The MCP service returned an invalid tool result.");
    }
    if (reply.isError === true) {
      throw new DeslopError("tool_error", "Zero Slop could not return a safely checked result. The source was not changed locally.");
    }
    return validateResult(reply.structuredContent);
  } catch (error) {
    if (controller.signal.aborted) throw controller.signal.reason;
    if (error instanceof DeslopError) throw error;
    throw new DeslopError("network_error", "The hosted MCP request failed. Its outcome may be unknown; no retry was sent.");
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", cancel);
    controller.signal.removeEventListener("abort", notifyCancellation);
  }
}
