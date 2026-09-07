// Synthetic MCP transport for unit tests and --import process tests. No network.
export function report(score = 9.5) {
  return {
    score, band: "clear", words: 20, sentences: 2, flaggedPhrases: 0,
    sentenceVariety: "natural", readability: "clear",
    punctuation: { dashes: 0, emoji: 0, hashtags: 0 }, highWeightFlags: 0,
    shape: { measured: false, broetry: false, oneSentenceParagraphShare: null, longestFragmentRun: null },
    register: { measured: true, words: 20, checked: 10, findings: [], twoPartContrasts: 0, announcements: 0 },
    flags: [],
  };
}

export function result(status = "rewritten") {
  const clear = status === "already_clear";
  return {
    text: "# Update\n\nMaya will send the €24,800 budget by Friday.\n",
    status, before: report(clear ? 9.5 : 70.1), after: report(9.5),
    scoreChange: clear ? 0 : -60.6, factsPreserved: true,
    passedFinalChecks: status === "rewritten", independentModelChecks: 0,
    modelRequests: clear ? 0 : 1, rolesCompleted: clear ? 1 : 8,
    finishingRounds: clear ? 0 : 1, scorerVersion: "2.10.0", durationMs: 42,
    note: clear ? "The draft already reads cleanly." : "One editorial response; local checks approved the result.",
  };
}

export function mockFetch(mode = "json", requests = [], send = () => {}) {
  return async (url, options) => {
    if (url !== "https://mcp.zero-slop.ai/mcp") throw new Error("Unexpected network destination");
    const body = JSON.parse(options.body);
    const record = { url, body, headers: Object.fromEntries(new Headers(options.headers)), redirect: options.redirect };
    requests.push(record);
    send({ type: "request", ...record });
    const waitForAbort = () => new Promise((resolve, reject) => {
      if (options.signal.aborted) reject(options.signal.reason);
      else options.signal.addEventListener("abort", () => reject(options.signal.reason), { once: true });
    });
    const packet = (value) => ({ jsonrpc: "2.0", id: body.id, result: value });
    if (body.method === "initialize") {
      if (mode === "initialize-hang") return waitForAbort();
      if (mode === "network") throw new Error("PRIVATE SERVER TEXT SHOULD NOT REACH OUTPUT");
      return Response.json(packet({ protocolVersion: mode === "unsupported" ? "2099-01-01" : mode === "session" ? "2025-06-18" : "2025-11-25",
        capabilities: { tools: {} }, serverInfo: { name: "zero-slop", version: "2.10.0" } }),
      { headers: mode === "session" ? { "mcp-session-id": "safe-session-1" }
        : mode === "bad-session" ? { "mcp-session-id": "x".repeat(513) } : {} });
    }
    if (body.method.startsWith("notifications/")) return new Response(null, { status: 202 });
    if (body.method !== "tools/call" || body.params.name !== "deslop") throw new Error("Unexpected tool");
    if (mode === "hang") return waitForAbort();
    if (mode === "http429") return new Response("PRIVATE SERVER TEXT", { status: 429, headers: { "retry-after": "10" } });
    if (mode === "redirect") return new Response("", { status: 307, headers: { location: "https://example.invalid/collect" } });
    if (mode === "rpc-error") return Response.json({ jsonrpc: "2.0", id: body.id, error: { code: -32602, message: "PRIVATE SERVER TEXT" } });
    if (mode === "tool-error") return Response.json(packet({ isError: true, content: [{ type: "text", text: "PRIVATE SERVER TEXT" }] }));
    if (["usage-limit", "budget-unavailable", "bad-budget"].includes(mode)) return Response.json(packet({ isError: true,
      content: [{ type: "text", text: "PRIVATE SERVER TEXT" }],
      _meta: { "zero-slop/error": { code: mode === "budget-unavailable" ? "budget_unavailable" : "usage_limit",
        status: mode === "budget-unavailable" ? 503 : 429, retryAfterSeconds: mode === "bad-budget" ? "PRIVATE SERVER TEXT" : 86_400 } },
    }));
    if (mode === "missing-result") return Response.json(packet({ content: [{ type: "text", text: "PRIVATE SERVER TEXT" }] }));
    if (mode === "malformed-json") return new Response("not-json PRIVATE SERVER TEXT", { headers: { "content-type": "application/json" } });
    if (mode === "bad-utf8") return new Response(new Uint8Array([0xff]), { headers: { "content-type": "application/json" } });
    if (mode === "wrong-type") return new Response("PRIVATE SERVER TEXT", { headers: { "content-type": "text/html" } });
    if (mode === "sse-truncated") return new Response('data: {"jsonrpc":"2.0","id":2,"result":{}', { headers: { "content-type": "text/event-stream" } });
    const status = mode.startsWith("status:") ? mode.slice(7) : "rewritten";
    const data = result(status);
    if (mode === "bad-report") data.after.score = 101;
    if (mode === "extra") { data.futureMetadata = { preserved: true }; data.after.futureMetric = "kept"; }
    const reply = packet({ structuredContent: data, ...(mode === "bad-is-error" ? { isError: "true" } : {}) });
    if (mode === "wrong-id") reply.id = 999;
    if (mode === "large") data.text = "x".repeat(9 * 1024 * 1024);
    if (mode === "body-hang") return new Response(new ReadableStream({ cancel() { send({ type: "body-cancelled" }); } }), { headers: { "content-type": "text/event-stream" } });
    if (mode === "sse") {
      const raw = `: heartbeat\r\n\r\ndata: {"jsonrpc":"2.0","method":"notifications/progress","params":{}}\r\n\r\n`
        + `data: {"jsonrpc":"2.0","id":999,"result":{}}\r\n\r\n`
        + JSON.stringify(reply, null, 2).split("\n").map((line) => `data: ${line}`).join("\r\n") + "\r\n\r\n";
      const bytes = new TextEncoder().encode(raw);
      let offset = 0;
      return new Response(new ReadableStream({
        pull(controller) {
          if (offset < bytes.length) { controller.enqueue(bytes.slice(offset, offset + 7)); offset += 7; }
          // Intentionally stay open after the result: the client must stop reading.
        },
        cancel() { send({ type: "body-cancelled" }); },
      }), { headers: { "content-type": "text/event-stream; charset=utf-8" } });
    }
    return Response.json(reply);
  };
}

if (process.env.ZERO_SLOP_TEST_TRANSPORT) {
  globalThis.fetch = mockFetch(process.env.ZERO_SLOP_TEST_TRANSPORT, [], (message) => process.send?.(message));
  if (process.env.ZERO_SLOP_TEST_TRANSPORT === "input-wait") {
    const iterator = process.stdin[Symbol.asyncIterator].bind(process.stdin);
    process.stdin[Symbol.asyncIterator] = (...args) => {
      process.send?.({ type: "input-read" });
      return iterator(...args);
    };
  }
}
