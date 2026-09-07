// Maintainer-only, opt-in check. Sends one synthetic draft to the public MCP.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

if (!process.argv.includes("--live")) {
  console.error("Run with --live to check the adapter using one synthetic draft.");
  process.exit(2);
}
const directory = fileURLToPath(new URL(".", import.meta.url));
const probe = createServer();
await new Promise((resolve, reject) => {
  probe.once("error", reject);
  probe.listen(0, "127.0.0.1", resolve);
});
const port = probe.address().port;
await new Promise(resolve => probe.close(resolve));
const remote = "https://mcp.zero-slop.ai/mcp";
const endpoint = `http://127.0.0.1:${port}/mcp`;
const child = spawn(process.execPath, [
  `${directory}node_modules/mcp-proxy/dist/bin/mcp-proxy.mjs`,
  "--host", "127.0.0.1", "--port", String(port), "--",
  process.execPath, `${directory}node_modules/mcp-remote/dist/proxy.js`,
  remote, "--transport", "http-only", "--silent",
], {
  cwd: directory,
  env: { PATH: process.env.PATH },
  stdio: ["ignore", "pipe", "pipe"],
});
let diagnosticBytes = 0;
for (const stream of [child.stdout, child.stderr]) {
  stream.on("data", chunk => { diagnosticBytes += chunk.length; });
}
let session;
let id = 0;
async function rpc(url, method, params = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      ...(url === endpoint && session ? { "Mcp-Session-Id": session } : {}),
    },
    body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }),
    signal: AbortSignal.timeout(20000),
  });
  assert.equal(response.status, 200);
  if (url === endpoint && response.headers.has("mcp-session-id")) {
    session = response.headers.get("mcp-session-id");
  }
  const body = await response.text();
  const parsed = response.headers.get("content-type").includes("text/event-stream")
    ? JSON.parse(body.split("\n").find(line => line.startsWith("data:")).slice(5))
    : JSON.parse(body);
  assert.equal(parsed.error, undefined);
  return parsed.result;
}
try {
  let ready = false;
  for (let attempt = 0; attempt < 40; attempt++) {
    try {
      ready = (await fetch(`http://127.0.0.1:${port}/ping`, {
        signal: AbortSignal.timeout(1000),
      })).ok;
    } catch { /* Wait for this local process only; never retry hosted editing. */ }
    if (ready || child.exitCode !== null) break;
    await delay(250);
  }
  assert.equal(ready, true, "Local bridge must start");
  const initialized = await rpc(endpoint, "initialize", {
    protocolVersion: "2025-03-26", capabilities: {},
    clientInfo: { name: "zero-slop-glama-acceptance", version: "1.0.0" },
  });
  assert.equal(initialized.serverInfo.name, "zero-slop");
  const [throughAdapter, direct] = await Promise.all([
    rpc(endpoint, "tools/list"), rpc(remote, "tools/list"),
  ]);
  assert.deepEqual(throughAdapter.tools, direct.tools);
  assert.deepEqual(direct.tools.map(tool => tool.name), ["deslop"]);
  const result = await rpc(endpoint, "tools/call", {
    name: "deslop",
    arguments: { text: "The cache expires after 15 minutes.", genre: "professional" },
  });
  assert.notEqual(result.isError, true);
  assert.equal(result.structuredContent.status, "already_clear");
  assert.equal(result.structuredContent.modelRequests, 0);
  assert.equal(result.structuredContent.factsPreserved, true);
  console.log(JSON.stringify({
    server: initialized.serverInfo,
    toolSchemaMatchesDirect: true,
    schemaSha256: createHash("sha256").update(JSON.stringify(direct.tools)).digest("hex"),
    syntheticCall: { status: "already_clear", modelRequests: 0, factsPreserved: true },
    diagnosticBytes,
  }, null, 2));
} finally {
  if (session) {
    await fetch(endpoint, { method: "DELETE", headers: { "Mcp-Session-Id": session },
      signal: AbortSignal.timeout(2000) }).catch(() => {});
  }
  child.kill("SIGTERM");
}
