// Real HTTP against a loopback fixture server. Never calls the hosted editor.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { delimiter, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { result } from "../../tests/fixtures/mcp-transport.mjs";

const root = dirname(fileURLToPath(import.meta.url));
const input = await readFile(join(root, "request.json"), "utf8");
const directory = await mkdtemp(join(tmpdir(), "zero-slop-api-examples-"));

function run(command, args, { env = {}, cwd = root, stdin = input, timeout = 20_000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", ...env }, shell: false });
    let stdout = "", stderr = "";
    const timer = setTimeout(() => { child.kill("SIGKILL"); reject(new Error(`${command} timed out`)); }, timeout);
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.stdin.on("error", () => {});
    child.on("error", (error) => { clearTimeout(timer); resolve({ code: -1, stdout, stderr: error.message }); });
    child.on("close", (code) => { clearTimeout(timer); resolve({ code, stdout, stderr }); });
    child.stdin.end(stdin);
  });
}

async function available(command, argument = "--version") {
  return (await run(command, [argument], { stdin: "" })).code === 0;
}

const commands = [
  { name: "JavaScript", command: process.execPath, args: [join(root, "javascript/deslop.mjs")] },
  { name: "TypeScript", command: process.execPath, args: ["--experimental-strip-types", join(root, "typescript/deslop.ts")] },
  { name: "Python", command: "python3", args: [join(root, "python/deslop.py")], ready: await available("python3") },
  { name: "curl", command: "sh", args: [join(root, "curl/deslop.sh")], ready: await available("curl") && await available("jq") },
];

// Optional compiled examples: set a binary/classpath after building, or let Go
// compile its standard-library sample into the isolated temporary directory.
const goBinary = process.env.ZERO_SLOP_GO_EXAMPLE ?? join(directory, "go-example");
let goReady = Boolean(process.env.ZERO_SLOP_GO_EXAMPLE);
if (!goReady && await available("go", "version")) {
  const build = await run("go", ["build", "-o", goBinary, join(root, "go/main.go")], { stdin: "", timeout: 180_000 });
  assert.equal(build.code, 0, build.stderr);
  goReady = true;
}
commands.push({ name: "Go", command: goBinary, args: [], ready: goReady });
commands.push({ name: "Java", command: "java", args: ["-cp", process.env.ZERO_SLOP_JAVA_CP ??
  [join(root, "java/target/classes"), join(root, "java/target/dependency/*")].join(delimiter), "Deslop"],
  ready: Boolean(process.env.ZERO_SLOP_JAVA_CP) && await available("java", "-version") });
commands.push({ name: "C#", command: "dotnet", args: [process.env.ZERO_SLOP_CSHARP_DLL ?? ""],
  ready: Boolean(process.env.ZERO_SLOP_CSHARP_DLL) && await available("dotnet") });
commands.push({ name: "Rust", command: process.env.ZERO_SLOP_RUST_EXAMPLE ?? "", args: [],
  ready: Boolean(process.env.ZERO_SLOP_RUST_EXAMPLE) });

const cases = [
  ...["rewritten", "rewritten_with_warnings", "already_clear", "unchanged_no_better_version", "unchanged_verification_failed", "unchanged_service_unavailable"]
    .map((status) => ({ name: status, status: 200, body: result(status), code: ["rewritten", "already_clear"].includes(status) ? 0 : 3 })),
  { name: "future status", status: 200, body: { ...result(), status: "future_status" }, code: 3 },
  { name: "string boolean", status: 200, body: { ...result(), factsPreserved: "true" }, code: 3 },
  { name: "string checks", status: 200, body: { ...result(), passedFinalChecks: "true" }, code: 3 },
  { name: "missing report score", status: 200, body: { ...result("already_clear"), before: {}, after: {} }, code: 3 },
  { name: "inconsistent clear score", status: 200, body: { ...result("already_clear"), scoreChange: -1 }, code: 3 },
  { name: "boolean request count", status: 200, body: { ...result("already_clear"), modelRequests: false }, code: 3 },
  { name: "additive field", status: 200, body: { ...result(), futureField: { value: "preserve me" } }, code: 0 },
  ...[[429, "capacity_limit", "10"], [429, "usage_limit", "3600"], [503, "budget_unavailable", null], [400, "invalid_input", null]]
    .map(([status, code, retryAfter]) => ({ name: code, status, retryAfter, code: 1,
      body: { type: "about:blank", title: status === 429 ? "Too Many Requests" : "Request failed", status,
        detail: "Synthetic problem; review before retrying.", code, requestId: "11111111-1111-4111-8111-111111111111" } })),
  { name: "redirect is not followed", status: 307, code: 1, location: "/unexpected",
    body: { type: "about:blank", title: "Redirect", status: 307, code: "fixture_redirect", detail: "Fixture", requestId: "fixture" } },
  { name: "malformed success JSON", status: 200, code: 1, raw: "<html>synthetic unavailable response</html>" },
];

for (const entry of commands) {
  test(`${entry.name}: contract outcomes, structured errors, no retries or redirects`, async (t) => {
    if (entry.ready === false) {
      if (process.env.ZERO_SLOP_REQUIRE_ALL_EXAMPLES === "1") assert.fail(`${entry.name}: required compiler or prepared binary is unavailable`);
      t.skip("Runtime or prepared binary unavailable; see README for compilation commands.");
      return;
    }
    let fixture, requests = [];
    const server = createServer(async (request, response) => {
      const chunks = [];
      for await (const chunk of request) chunks.push(chunk);
      requests.push({ method: request.method, url: request.url, contentType: request.headers["content-type"], body: Buffer.concat(chunks).toString("utf8") });
      response.writeHead(fixture.status, { "Content-Type": fixture.status === 200 ? "application/json" : "application/problem+json",
        ...(fixture.retryAfter ? { "Retry-After": fixture.retryAfter } : {}), ...(fixture.location ? { Location: fixture.location } : {}) });
      response.end(fixture.raw ?? JSON.stringify(fixture.body));
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    t.after(() => server.close());
    const endpoint = `http://127.0.0.1:${server.address().port}/v1/deslop`;
    for (fixture of cases) {
      requests = [];
      const output = await run(entry.command, entry.args, { env: { ZERO_SLOP_API_URL: endpoint } });
      assert.equal(output.code, fixture.code, `${fixture.name}: ${output.stderr}`);
      assert.equal(requests.length, 1, `${fixture.name}: request must never be replayed`);
      assert.equal(requests[0].method, "POST");
      assert.equal(requests[0].url, "/v1/deslop");
      assert.match(requests[0].contentType, /^application\/json/);
      assert.deepEqual(JSON.parse(requests[0].body), JSON.parse(input));
      if (fixture.raw) {
        assert.equal(output.stdout, "");
        assert.match(output.stderr, /JSON/);
      } else if (fixture.status === 200) {
        assert.deepEqual(JSON.parse(output.stdout), fixture.body, `${fixture.name}: preserve complete result`);
      } else {
        assert.equal(output.stdout, "");
        const error = JSON.parse(output.stderr);
        assert.equal(error.httpStatus, fixture.status);
        assert.equal(error.retryAfter, fixture.retryAfter ?? null);
        assert.deepEqual(error.problem, fixture.body);
      }
    }
    t.diagnostic(`${cases.length} fixture outcomes passed; no hosted calls.`);
  });
}
