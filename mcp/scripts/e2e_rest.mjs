#!/usr/bin/env node
// Maintainer-only, credential-free HTTP checks. Never imported by the runtime.
// Probe only: node mcp/scripts/e2e_rest.mjs --base-url https://mcp.zero-slop.ai
// No inference: add --run. Exactly two synthetic drafts: add --run --allow-inference.
// No retries, redirects, private drafts, output files, or forced capacity failures.
import { pathToFileURL } from "node:url";
import { gzipSync } from "node:zlib";
import { GENRES, RESULT_STATUSES, isApprovedResult, validateResult } from "../../bin/lib/deslop.mjs";

export const REQUEST_BUDGET_MS = 75_000;
const MAX_RESPONSE_BYTES = 8 * 1024 * 1024;
const MAX_REQUEST_BYTES = 128 * 1024;
const RESULT_FIELDS = Object.freeze([
  "text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
  "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note",
]);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const JSON_HEADERS = { "content-type": "application/json" };
const SYNTHETIC_DRAFTS = Object.freeze([
  { text: "Maya owns the pricing review. The team will decide on Friday.", genre: "professional" },
  { text: "It is important to note that Maya owns the pricing review. As we move forward, the team will leverage the proposal to make a decision on Friday. This represents a significant milestone in our journey.", genre: "professional", audience: "The project team" },
]);

class CheckError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}
function check(condition, message) {
  if (!condition) throw new CheckError("assertion_failed", message);
}

export function validateBaseUrl(value) {
  let url;
  try { url = new URL(value); } catch { throw new CheckError("invalid_options", "Provide an absolute --base-url."); }
  const loopback = ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
  check((url.protocol === "https:" || (url.protocol === "http:" && loopback))
    && !url.username && !url.password && !url.search && !url.hash && url.pathname === "/",
  "The base URL must be an HTTPS origin, or loopback HTTP, without credentials, path, query, or fragment.");
  return url.origin;
}

export function parseOptions(args) {
  const options = { run: false, allowInference: false };
  const seen = new Set();
  for (let index = 0; index < args.length; index++) {
    const arg = args[index];
    check(!seen.has(arg), "Do not repeat command options.");
    seen.add(arg);
    if (arg === "--base-url") options.baseUrl = validateBaseUrl(args[++index]);
    else if (arg === "--run") options.run = true;
    else if (arg === "--allow-inference") options.allowInference = true;
    else if (arg === "--help") options.help = true;
    else throw new CheckError("invalid_options", "Unknown option. Use --help.");
  }
  if (!options.help) {
    check(Boolean(options.baseUrl), "--base-url is required; there is no implicit production target.");
    check(!options.allowInference || options.run, "--allow-inference also requires --run.");
  }
  return options;
}

// The budget covers DNS, TLS, response headers AND the entire response body.
export async function requestHttp(baseUrl, path, init = {}, options = {}) {
  const timeoutMs = options.timeoutMs ?? REQUEST_BUDGET_MS;
  check(Number.isSafeInteger(timeoutMs) && timeoutMs >= 1 && timeoutMs <= REQUEST_BUDGET_MS,
    "A request budget must be between 1 and 75,000 milliseconds.");
  check(path.startsWith("/") && !path.startsWith("//"), "Requests must stay on the selected origin.");
  const origin = validateBaseUrl(baseUrl);
  const destination = new URL(path, origin);
  check(destination.origin === origin, "Requests must stay on the selected origin.");
  const controller = new AbortController();
  const started = performance.now();
  let reader;
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      void reader?.cancel().catch(() => {});
      reject(new CheckError("timeout", "The request exceeded its total budget. No retry was sent."));
    }, timeoutMs);
  });
  const operation = (async () => {
    const response = await (options.fetchImpl ?? fetch)(destination, {
      ...init,
      headers: { accept: "application/json, application/problem+json", "cache-control": "no-store", ...init.headers },
      redirect: "manual", credentials: "omit", signal: controller.signal,
    });
    const chunks = [];
    let bytes = 0;
    if (response.body) {
      reader = response.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        check(bytes <= MAX_RESPONSE_BYTES, "Response exceeded the bounded 8 MiB reader.");
        chunks.push(value);
      }
    }
    controller.signal.throwIfAborted();
    let raw;
    try { raw = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks, bytes)); }
    catch { throw new CheckError("invalid_response", "Response was not valid UTF-8."); }
    return { status: response.status, headers: response.headers, raw, bytes, durationMs: Math.round(performance.now() - started) };
  })();
  try { return await Promise.race([operation, timeout]); }
  catch (error) {
    if (error instanceof CheckError) throw error;
    throw new CheckError("network_error", "The request or response stream failed. No retry was sent.");
  } finally {
    clearTimeout(timer);
    controller.abort();
    void reader?.cancel().catch(() => {});
  }
}

function json(response, contentType = "application/json") {
  check(response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase() === contentType, "Unexpected response content type.");
  try { return JSON.parse(response.raw); }
  catch { throw new CheckError("invalid_response", "Response was not valid JSON."); }
}

function securityHeaders(response) {
  check(response.headers.get("cache-control")?.split(/\s*,\s*/).includes("no-store"), "Response must not be cached.");
  check(response.headers.get("x-content-type-options") === "nosniff", "Missing nosniff response protection.");
  check(response.headers.get("x-frame-options") === "DENY", "Missing frame protection.");
  check(response.headers.get("referrer-policy") === "no-referrer", "Missing no-referrer policy.");
  check(!response.headers.has("access-control-allow-origin"), "REST must not enable cross-origin browser access.");
  check(!response.headers.has("set-cookie"), "Public REST checks must not establish cookie sessions.");
}

export function assertOpenApi(response) {
  check(response.status === 200, "OpenAPI is not available at HTTP 200; no further checks were sent.");
  securityHeaders(response);
  const schema = json(response);
  check(/^3\.1\.\d+$/.test(schema.openapi), "Expected OpenAPI 3.1.");
  check(typeof schema.info?.version === "string" && /^[0-9A-Za-z.+_-]{1,64}$/.test(schema.info.version), "Missing bounded API release version.");
  const operation = schema.paths?.["/v1/deslop"]?.post;
  check(operation?.operationId === "deslop", "Missing deslop operation.");
  check(Array.isArray(operation.security) && operation.security.length === 0, "The public operation must require no credentials.");
  check(!schema.components?.securitySchemes || Object.keys(schema.components.securitySchemes).length === 0, "Unexpected public API credential schemes.");
  const input = schema.components?.schemas?.DeslopInput;
  const output = schema.components?.schemas?.DeslopResult;
  check(input?.properties?.text?.maxLength === 20_000 && input?.properties?.audience?.maxLength === 200, "Input character limits drifted.");
  check(JSON.stringify(input?.properties?.genre?.enum) === JSON.stringify(GENRES), "Genre contract drifted.");
  check(RESULT_FIELDS.every((key) => output?.required?.includes(key) && output?.properties?.[key]), "OpenAPI is missing required result fields.");
  check(JSON.stringify(output.properties.status.enum) === JSON.stringify(RESULT_STATUSES), "Result statuses drifted.");
  for (const status of [200, 400, 405, 408, 413, 415, 429, 503]) check(operation.responses?.[status], "Missing documented HTTP outcome.");
  return { openapi: schema.openapi, version: schema.info?.version, requiredResultFields: RESULT_FIELDS.length };
}

export function assertProblem(response, status, code) {
  check(response.status === status, `Expected HTTP ${status}; received HTTP ${response.status}.`);
  securityHeaders(response);
  const body = json(response, "application/problem+json");
  check(body.type === "about:blank" && body.status === status && body.code === code, "Unexpected problem classification.");
  check(typeof body.title === "string" && Boolean(body.title) && typeof body.detail === "string", "Missing structured problem details.");
  check(UUID.test(body.requestId) && response.headers.get("x-request-id") === body.requestId, "Request ID must match the structured problem.");
  if (status === 429) check(/^[1-9][0-9]{0,5}$/.test(response.headers.get("retry-after") ?? ""), "Capacity rejection must provide a positive Retry-After delay.");
  check(!/e2e-private-canary/.test(response.raw), "An invalid draft was echoed in an error.");
}

export function assertPipeline(response, original) {
  check(response.status === 200, `Expected a pipeline outcome; received HTTP ${response.status}. No retry was sent.`);
  securityHeaders(response);
  check(UUID.test(response.headers.get("x-request-id") ?? ""), "Missing pipeline request ID.");
  let result;
  try { result = validateResult(json(response)); }
  catch { throw new CheckError("invalid_response", "Pipeline outcome failed the shared CLI/MCP result validator."); }
  check(RESULT_FIELDS.every((key) => Object.hasOwn(result, key)), "Pipeline result is missing required fields.");
  const scoreChange = Math.round((result.after.score - result.before.score) * 10) / 10;
  check(Math.abs(result.scoreChange - scoreChange) < 0.00001, "Score change does not match before and after.");
  if (result.status === "already_clear" || result.status.startsWith("unchanged_")) {
    check(result.text === original.trim(), "An unchanged outcome must preserve the original draft.");
    check(result.scoreChange === 0 && result.before.score === result.after.score, "An unchanged outcome must preserve its score.");
  }
  if (result.status === "already_clear") check(isApprovedResult(result), "An already-clear result has inconsistent checks or model work.");
  return {
    pipelineStatus: result.status, approved: isApprovedResult(result), modelRequests: result.modelRequests,
    beforeScore: result.before.score, afterScore: result.after.score, scorerVersion: result.scorerVersion,
    factsPreserved: result.factsPreserved, passedFinalChecks: result.passedFinalChecks,
  };
}

function invalidCases() {
  const post = (name, body, status = 400, code = "invalid_input", headers = JSON_HEADERS) => ({ name, path: "/v1/deslop", init: { method: "POST", headers, body }, status, code });
  const encode = (value) => JSON.stringify(value);
  // Syntactically valid, but oversized and empty: even a broken byte gate must not run a model.
  const oversized = Buffer.alloc(MAX_REQUEST_BYTES + 1, 0x20);
  oversized.write('{"text":""}');
  const chunked = new ReadableStream({ start(controller) { controller.enqueue(oversized.subarray(0, 65536)); controller.enqueue(oversized.subarray(65536)); controller.close(); } });
  return [
    { name: "OpenAPI rejects POST", path: "/openapi.json", init: { method: "POST" }, status: 405, code: "method_not_allowed", allow: "GET, HEAD" },
    { name: "REST rejects GET", path: "/v1/deslop", init: {}, status: 405, code: "method_not_allowed", allow: "POST" },
    { name: "Third-party browser preflight is rejected", path: "/v1/deslop", init: { method: "OPTIONS", headers: { origin: "https://example.invalid", "access-control-request-method": "POST" } }, status: 403, code: "forbidden_origin" },
    post("Malformed JSON", '{"text":"e2e-private-canary"', 400, "invalid_json"),
    post("Malformed UTF-8", Buffer.concat([Buffer.from('{"text":"e2e-private-canary'), Buffer.from([0xff]), Buffer.from('"}')]), 400, "invalid_json"),
    post("Missing text", "{}"),
    post("Whitespace-only text", encode({ text: " \n\t " })),
    post("Non-string text", encode({ text: 42 })),
    post("Unsupported genre", encode({ text: "e2e-private-canary", genre: "not-a-genre" })),
    post("Non-string audience", encode({ text: "e2e-private-canary", audience: false })),
    post("ASCII text over 20,000 code points", encode({ text: "x".repeat(20_001) })),
    post("Astral text over 20,000 code points", encode({ text: "😀".repeat(20_001) })),
    post("Astral audience over 200 code points", encode({ text: "e2e-private-canary", audience: "😀".repeat(201) })),
    post("Unsupported media type", "{}", 415, "unsupported_media_type", { "content-type": "text/plain" }),
    post("Missing media type", Buffer.from("{}"), 415, "unsupported_media_type", {}),
    post("Compressed body rejected", gzipSync('{"text":""}'), 415, "unsupported_media_type", { ...JSON_HEADERS, "content-encoding": "gzip" }),
    post("Identity encoding accepted before validation", '{"text":""}', 400, "invalid_input", { ...JSON_HEADERS, "content-encoding": "identity" }),
    post("Declared body over 128 KiB", oversized, 413, "request_too_large"),
    { ...post("Streamed body over 128 KiB", chunked, 413, "request_too_large"), init: { method: "POST", headers: JSON_HEADERS, body: chunked, duplex: "half" } },
  ];
}

export async function runSuite(options, transport = {}) {
  const baseUrl = validateBaseUrl(options.baseUrl);
  check(!options.allowInference || options.run, "Inference requires the explicit full-run option.");
  const report = { baseUrl, mode: options.run ? (options.allowInference ? "synthetic-e2e" : "http-validation") : "probe", requestBudgetMs: REQUEST_BUDGET_MS, validDraftsSent: 0, passed: 0, failed: 0, checks: [] };
  async function perform(name, path, init, validate) {
    let response;
    try {
      response = await requestHttp(baseUrl, path, init, transport);
      const details = validate(response) ?? {};
      report.checks.push({ name, pass: true, httpStatus: response.status, durationMs: response.durationMs, ...details });
      report.passed++;
    } catch (error) {
      report.checks.push({ name, pass: false, ...(response ? { httpStatus: response.status, durationMs: response.durationMs } : {}), code: error instanceof CheckError ? error.code : "check_failed", message: error instanceof CheckError ? error.message : "The check failed; response content was not logged." });
      report.failed++;
    }
    // Fail fast: do not send further cases after unexpected responses or capacity errors.
    return report.failed === 0;
  }
  if (!await perform("OpenAPI GET and shared contract", "/openapi.json", {}, assertOpenApi) || !options.run) return report;
  if (!await perform("OpenAPI HEAD", "/openapi.json", { method: "HEAD" }, (response) => {
    check(response.status === 200 && response.bytes === 0, "HEAD must return HTTP 200 without a response body.");
    securityHeaders(response);
    check(response.headers.get("content-type")?.startsWith("application/json"), "HEAD must describe JSON.");
  })) return report;
  if (!await perform("Unknown REST route", "/v1/__zero_slop_e2e_missing", {}, (response) => {
    check(response.status === 404, "Unknown routes must return HTTP 404 without redirects.");
    securityHeaders(response);
    check(json(response).error === "not_found", "Unexpected missing-route response.");
  })) return report;
  for (const entry of invalidCases()) {
    if (!await perform(entry.name, entry.path, entry.init, (response) => {
      assertProblem(response, entry.status, entry.code);
      if (entry.allow) check(response.headers.get("allow") === entry.allow, "Method rejection must advertise allowed methods.");
    })) return report;
  }
  if (options.allowInference) {
    for (const [index, input] of SYNTHETIC_DRAFTS.entries()) {
      report.validDraftsSent++;
      if (!await perform(`Synthetic draft ${index + 1}: full pipeline contract`, "/v1/deslop", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(input) }, (response) => {
        const outcome = assertPipeline(response, input.text);
        check(outcome.scorerVersion === report.checks[0].version, "Pipeline release does not match the OpenAPI release.");
        return outcome;
      })) break;
    }
  }
  return report;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const options = parseOptions(process.argv.slice(2));
    if (options.help) {
      console.log("Usage: node mcp/scripts/e2e_rest.mjs --base-url https://mcp.zero-slop.ai [--run [--allow-inference]]\nDefaults to one GET probe. --run checks HTTP validation without valid drafts.\n--allow-inference additionally sends exactly two synthetic drafts, once each.\nEvery request is bounded to 75 seconds. No credentials, redirects, retries, or load tests.\nJSON reports omit draft and rewrite text. HTTP 200 is not automatic editorial approval.");
    } else {
      const report = await runSuite(options);
      console.log(JSON.stringify(report, null, 2));
      const reviewRequired = report.checks.filter((entry) => entry.approved === false).length;
      console.error(`${report.passed} passed; ${report.failed} failed; ${report.validDraftsSent} synthetic drafts sent; ${reviewRequired} outcomes require review. No retries.`);
      process.exitCode = report.failed ? 1 : 0;
    }
  } catch {
    console.error("Invalid E2E options. Use --help. No implicit production target or credentials are supported.");
    process.exitCode = 2;
  }
}
