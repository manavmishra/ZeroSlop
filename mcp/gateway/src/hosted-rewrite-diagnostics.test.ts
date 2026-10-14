import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { callRole, type EditorFailure } from "./model";
import { localRescue, runPipeline } from "./pipeline";

const source = "We’re thrilled to announce a game-changing update to Project Northstar. Starting October 20, teams can export their weekly report as a CSV file. It is important to note that Maya owns the rollout, and the beta is limited to 25 teams. This seamless experience empowers teams to unlock actionable insights.";
const observed = "We’re thrilled to announce a useful update to Project Northstar. Starting October 20, teams can export their weekly report as a CSV file. Maya owns the rollout, and the beta is limited to 25 teams. This seamless experience empowers teams to unlock actionable insights.";
const corePath = fileURLToPath(new URL("../../scorer/src", import.meta.url));
const python = "import json,sys;sys.path.insert(0,sys.argv[1]);import scorer_core as c;p=json.load(sys.stdin);print(json.dumps(c.report(p['text'],p['genre']) if sys.argv[2]=='/report' else c.rank(p['original'],p['candidates'],p['genre'])))";
const scorer = { fetch: async (url: RequestInfo | URL, init?: RequestInit) => Response.json(JSON.parse(execFileSync("python3", ["-c", python, corePath, new URL(String(url)).pathname], {
  input: String(init?.body), encoding: "utf8", env: { ...process.env, ZERO_SLOP_HOME: "/tmp/zero-slop-northstar-tests", ZERO_SLOP_NO_NOTES: "1", PYTHONDONTWRITEBYTECODE: "1" },
}))) };
const signingKey = "test-editor-signing-key-012345678901234567890";
const env = { SCORER: scorer, SCORER_VERSION: "2.12.22", EDITOR_ENDPOINT: "https://example.invalid/editor", EDITOR_SHARED_SECRET: signingKey } as unknown as Env;

test("the observed fallback has the reported score without changing the scorer", async () => {
  const report = await (await scorer.fetch("https://scorer/report", { body: JSON.stringify({ text: observed, genre: "social" }) })).json() as { score: number; flaggedPhrases: number };
  assert.equal(report.score, 99.9);
  assert.equal(report.flaggedPhrases, 4);
});

test("Northstar provider outage and rejected source edit have distinct review warnings", async () => {
  const oldFetch = globalThis.fetch;
  try {
    globalThis.fetch = (async () => Response.json({ error: "editor_unavailable", editorOutcome: "unavailable", providerCalls: 2 }, { status: 503 })) as typeof fetch;
    const unavailable = await runPipeline(env, { text: source, genre: "social", audience: "product managers" });
    assert.equal(unavailable.text, localRescue(source));
    assert.notEqual(unavailable.text, observed);
    assert.equal(unavailable.before.score, 100);
    assert.ok(unavailable.after.score < 99.9);
    assert.equal(unavailable.modelRequests, 2);
    assert.equal(unavailable.status, "rewritten_with_warnings");
    assert.equal(unavailable.passedFinalChecks, false);
    assert.equal(unavailable.factsPreserved, true);
    assert.match(unavailable.note, /editor service was unavailable/);
    assert.doesNotMatch(unavailable.note, /did not pass the source check/);

    globalThis.fetch = (async () => Response.json({ rewrite: localRescue(source).replace("25 teams", "250 teams"), provider: "mock", model: "mock", stored: false, providerCalls: 2 })) as typeof fetch;
    const rejected = await runPipeline(env, { text: source, genre: "social" });
    assert.equal(rejected.text, unavailable.text);
    assert.match(rejected.note, /model response did not pass the source check/);
    assert.doesNotMatch(rejected.note, /was unavailable/);
    assert.equal(rejected.factsPreserved, true);
    assert.equal(rejected.passedFinalChecks, false);

    globalThis.fetch = (async () => Response.json({ error: "editor_timeout", editorOutcome: "timeout", providerCalls: 2 }, { status: 503 })) as typeof fetch;
    const timeout = await runPipeline(env, { text: source, genre: "social" });
    assert.match(timeout.note, /editor request timed out/);
    assert.equal(timeout.text, unavailable.text);
    assert.equal(timeout.passedFinalChecks, false);
  } finally { globalThis.fetch = oldFetch; }
});

test("a provider ignoring cancellation still reaches the bounded editor timeout", async () => {
  const oldFetch = globalThis.fetch;
  let failure: EditorFailure | null = null;
  globalThis.fetch = (async () => new Promise<Response>(() => {})) as typeof fetch;
  try {
    const result = await callRole(env, "complete", source, {}, Date.now() + 800, "", undefined, undefined, value => { failure = value; });
    assert.equal(result, null);
    assert.equal(failure, "timeout");
  } finally { globalThis.fetch = oldFetch; }
});

test("failure logs contain fixed categories, never arbitrary error names, source or secrets", async () => {
  const oldFetch = globalThis.fetch;
  const oldWarn = console.warn;
  const logs: string[] = [];
  globalThis.fetch = (async () => { const error = new Error(source); error.name = signingKey; throw error; }) as typeof fetch;
  console.warn = (value: string) => { logs.push(value); };
  try {
    await callRole(env, "complete", source, {}, Date.now() + 1000);
    assert.equal(JSON.parse(logs[0]!).reason, "transport");
    assert.ok(logs.every(value => !value.includes(source) && !value.includes(signingKey)));
  } finally { globalThis.fetch = oldFetch; console.warn = oldWarn; }
});

test("an invalid HTTP success body differs from an unproven provider abort", async () => {
  const oldFetch = globalThis.fetch;
  try {
    for (const [reply, expected] of [
      [async () => new Response("not JSON"), "invalid_output"],
      [async () => { throw new DOMException("provider stopped", "AbortError"); }, "transport"],
    ] as const) {
      let failure: EditorFailure | null = null;
      globalThis.fetch = reply as typeof fetch;
      assert.equal(await callRole(env, "complete", source, {}, Date.now() + 1000, "", undefined, undefined, value => { failure = value; }), null);
      assert.equal(failure, expected);
    }
  } finally { globalThis.fetch = oldFetch; }
});

test("already clear Northstar facts require no provider request", async () => {
  const text = "Starting October 20, teams can export their weekly report as a CSV file. Maya owns the rollout, and the beta is limited to 25 teams.";
  const oldFetch = globalThis.fetch;
  globalThis.fetch = (async () => { throw new Error("must not call editor"); }) as typeof fetch;
  try {
    const result = await runPipeline(env, { text, genre: "social" });
    assert.equal(result.text, text);
    assert.equal(result.status, "already_clear");
    assert.equal(result.modelRequests, 0);
    assert.equal(result.passedFinalChecks, false);
  } finally { globalThis.fetch = oldFetch; }
});

test("a model response that cleans back to the source is not a service outage", async () => {
  const text = "We are thrilled to announce that Maya owns the rollout on October 20 for 25 teams.";
  const oldFetch = globalThis.fetch;
  globalThis.fetch = (async () => Response.json({ rewrite: `It is important to note that ${text}`, provider: "mock", model: "mock", stored: false })) as typeof fetch;
  try {
    const result = await runPipeline(env, { text, genre: "social" });
    assert.equal(result.text, text);
    assert.equal(result.status, "unchanged_no_better_version");
    assert.match(result.note, /no distinct edit after local cleanup/);
    assert.doesNotMatch(result.note, /unavailable/);
    assert.equal(result.passedFinalChecks, false);
  } finally { globalThis.fetch = oldFetch; }
});
