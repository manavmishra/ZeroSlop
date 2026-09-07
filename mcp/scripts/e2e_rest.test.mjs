import assert from "node:assert/strict";
import { createServer } from "node:http";
import test from "node:test";
import { GENRES, RESULT_STATUSES } from "../../bin/lib/deslop.mjs";
import { result } from "../../tests/fixtures/mcp-transport.mjs";
import { assertPipeline, assertProblem, parseOptions, requestHttp, runSuite, validateBaseUrl } from "./e2e_rest.mjs";

const requestId = "cd570740-252f-48a7-a338-91d01c540b52";
const headers = {
  "content-type": "application/json", "cache-control": "no-store", "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff", "x-frame-options": "DENY", "x-request-id": requestId,
};
function problem(status, code) {
  return { type: "about:blank", title: "Synthetic problem", detail: "Synthetic fixture.", status, code, requestId };
}
function openApi() {
  return {
    openapi: "3.1.2", info: { version: "2.10.0" },
    paths: { "/v1/deslop": { post: { operationId: "deslop", security: [], responses: Object.fromEntries([200, 400, 405, 408, 413, 415, 429, 503].map((code) => [code, {}])) } } },
    components: { schemas: {
      DeslopInput: { properties: { text: { maxLength: 20_000 }, audience: { maxLength: 200 }, genre: { enum: GENRES } } },
      DeslopResult: { required: Object.keys(result()), properties: { ...Object.fromEntries(Object.keys(result()).map((key) => [key, {}])), status: { enum: RESULT_STATUSES } } },
    } },
  };
}
async function fixtureServer(t, handle) {
  const server = createServer((request, response) => {
    Promise.resolve(handle(request, response)).catch(() => { response.writeHead(500); response.end(); });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(async () => {
    server.closeAllConnections();
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  });
  return `http://127.0.0.1:${server.address().port}`;
}
function send(response, status, body, extra = {}) {
  response.writeHead(status, { ...headers, ...extra });
  response.end(body === undefined ? undefined : JSON.stringify(body));
}
function serializedResponse(payload, status = 200, extra = {}) {
  return { status, headers: new Headers({ ...headers, ...extra }), raw: JSON.stringify(payload) };
}

test("explicit origin and inference opt-in are mandatory", () => {
  assert.equal(validateBaseUrl("https://mcp.zero-slop.ai/"), "https://mcp.zero-slop.ai");
  assert.equal(validateBaseUrl("http://127.0.0.1:9999"), "http://127.0.0.1:9999");
  for (const origin of ["http://example.com", "https://name:secret@example.com", "https://example.com/path", "https://example.com?token=secret", "https://example.com#fragment"]) {
    assert.throws(() => validateBaseUrl(origin));
  }
  assert.throws(() => parseOptions([]));
  assert.throws(() => parseOptions(["--base-url", "https://mcp.zero-slop.ai", "--allow-inference"]));
  assert.throws(() => parseOptions(["--base-url", "https://mcp.zero-slop.ai", "--run", "--run"]));
  assert.deepEqual(parseOptions(["--base-url", "https://mcp.zero-slop.ai"]), { baseUrl: "https://mcp.zero-slop.ai", run: false, allowInference: false });
});

test("probe is one actual HTTP GET and never sends a draft", async (t) => {
  const requests = [];
  const baseUrl = await fixtureServer(t, (request, response) => {
    requests.push({ method: request.method, path: request.url, headers: request.headers });
    send(response, 200, openApi());
  });
  const report = await runSuite({ baseUrl });
  assert.equal(report.passed, 1);
  assert.equal(report.validDraftsSent, 0);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].method, "GET");
  assert.equal(requests[0].path, "/openapi.json");
  assert.equal(requests[0].headers.authorization, undefined);
  assert.equal(requests[0].headers.cookie, undefined);
});

test("full suite uses real HTTP, strict Unicode boundaries, and exactly two synthetic drafts", async (t) => {
  const received = [];
  let validDrafts = 0;
  const baseUrl = await fixtureServer(t, async (request, response) => {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    const body = Buffer.concat(chunks);
    received.push({ path: request.url, method: request.method, bytes: body.length, headers: request.headers });
    const reject = (status, code, extra) => send(response, status, problem(status, code), { "content-type": "application/problem+json", ...extra });
    if (request.url === "/openapi.json") {
      if (request.method === "HEAD") return send(response, 200);
      if (request.method !== "GET") return reject(405, "method_not_allowed", { allow: "GET, HEAD" });
      return send(response, 200, openApi());
    }
    if (request.url !== "/v1/deslop") return send(response, 404, { error: "not_found" });
    if (request.headers.origin && !["https://zero-slop.ai", "https://www.zero-slop.ai"].includes(request.headers.origin)) return reject(403, "forbidden_origin");
    if (request.method !== "POST") return reject(405, "method_not_allowed", { allow: "POST" });
    if (request.headers["content-type"] !== "application/json" || (request.headers["content-encoding"] && request.headers["content-encoding"] !== "identity")) return reject(415, "unsupported_media_type");
    if (body.length > 128 * 1024) return reject(413, "request_too_large");
    let input;
    try { input = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(body)); }
    catch { return reject(400, "invalid_json"); }
    const validText = typeof input?.text === "string" && input.text.trim() && [...input.text.trim()].length <= 20_000;
    const validAudience = input?.audience === undefined || (typeof input.audience === "string" && [...input.audience.trim()].length <= 200);
    if (!validText || !validAudience || (input.genre !== undefined && !GENRES.includes(input.genre))) return reject(400, "invalid_input");
    validDrafts++;
    const output = result(validDrafts === 1 ? "already_clear" : "rewritten");
    if (validDrafts === 1) output.text = input.text;
    return send(response, 200, output);
  });
  const report = await runSuite({ baseUrl, run: true, allowInference: true });
  assert.equal(report.failed, 0, JSON.stringify(report));
  assert.equal(report.passed, 24);
  assert.equal(report.validDraftsSent, 2);
  assert.equal(validDrafts, 2);
  assert.equal(received.length, 24);
  assert.equal(received.filter((request) => request.bytes > 128 * 1024).length, 2);
  assert(received.some((request) => request.headers["transfer-encoding"] === "chunked" && !request.headers["content-length"]));
  assert(received.every((request) => !request.headers.authorization && !request.headers.cookie));
  assert.equal(report.checks.at(-1).approved, true);
  assert(!JSON.stringify(report).includes("Maya"));
  assert(!JSON.stringify(report).includes("e2e-private-canary"));
});

test("404, 429, and 503 fail fast without retry or draft text in output", async (t) => {
  for (const status of [404, 429, 503]) {
    let calls = 0;
    const baseUrl = await fixtureServer(t, (_request, response) => {
      calls++;
      send(response, status, { text: "PRIVATE SERVER DRAFT", error: "PRIVATE ERROR" }, { "retry-after": "10" });
    });
    const report = await runSuite({ baseUrl, run: true, allowInference: true });
    assert.equal(calls, 1);
    assert.equal(report.failed, 1);
    assert.equal(report.validDraftsSent, 0);
    assert.equal(report.checks[0].httpStatus, status);
    assert(!JSON.stringify(report).includes("PRIVATE"));
  }
});

test("HTTP timeout bounds headers and body; redirects are never followed", async (t) => {
  const calls = [];
  const baseUrl = await fixtureServer(t, (request, response) => {
    calls.push(request.url);
    if (request.url === "/redirect") { response.writeHead(307, { location: "/destination" }); response.end(); }
    else if (request.url === "/body-hang") { response.writeHead(200, headers); response.write("{"); }
    // /headers-hang deliberately has no response; fixture cleanup closes the connection.
  });
  for (const path of ["/headers-hang", "/body-hang"]) {
    const started = performance.now();
    await assert.rejects(requestHttp(baseUrl, path, {}, { timeoutMs: 30 }), (error) => error.code === "timeout");
    assert(performance.now() - started < 1000);
  }
  assert.equal((await requestHttp(baseUrl, "/redirect")).status, 307);
  assert.deepEqual(calls, ["/headers-hang", "/body-hang", "/redirect"]);
  await assert.rejects(requestHttp(baseUrl, "//example.invalid"));
  await assert.rejects(requestHttp(baseUrl, "/", {}, { timeoutMs: 75_001 }));
});

test("response reader rejects invalid UTF-8 and over-limit bodies", async (t) => {
  const baseUrl = await fixtureServer(t, (request, response) => {
    response.writeHead(200, headers);
    response.end(request.url === "/utf8" ? Buffer.from([0xff]) : Buffer.alloc(8 * 1024 * 1024 + 1, 0x20));
  });
  await assert.rejects(requestHttp(baseUrl, "/utf8"), (error) => error.code === "invalid_response");
  await assert.rejects(requestHttp(baseUrl, "/oversized"), (error) => error.code === "assertion_failed");
});

test("full shared validator and approval predicate preserve warnings and reject inconsistent outcomes", () => {
  for (const status of RESULT_STATUSES) {
    const output = result(status);
    output.text = output.text.trim();
    if (status.startsWith("unchanged_")) { output.before = output.after; output.scoreChange = 0; }
    const info = assertPipeline(serializedResponse(output), output.text);
    assert.equal(info.approved, ["already_clear", "rewritten"].includes(status));
    assert.equal(info.pipelineStatus, status);
  }
  for (const field of Object.keys(result())) {
    const output = result();
    delete output[field];
    assert.throws(() => assertPipeline(serializedResponse(output), output.text));
  }
  const malformed = result();
  malformed.after.punctuation.emoji = -1;
  assert.throws(() => assertPipeline(serializedResponse(malformed), malformed.text));
  const inconsistent = result("already_clear");
  inconsistent.modelRequests = 1;
  assert.throws(() => assertPipeline(serializedResponse(inconsistent), inconsistent.text));
  assert.throws(() => assertPipeline(serializedResponse(result("unchanged_verification_failed")), "Different source."));
  const rateLimit = serializedResponse(problem(429, "capacity_limit"), 429, { "content-type": "application/problem+json", "retry-after": "10" });
  assert.doesNotThrow(() => assertProblem(rateLimit, 429, "capacity_limit"));
  assert.throws(() => assertPipeline(rateLimit, "Synthetic source."));
  rateLimit.headers.delete("retry-after");
  assert.throws(() => assertProblem(rateLimit, 429, "capacity_limit"));
  assert.doesNotThrow(() => assertProblem(serializedResponse(problem(503, "service_unavailable"), 503, { "content-type": "application/problem+json" }), 503, "service_unavailable"));
});
