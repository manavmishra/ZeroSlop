import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { callRole, type EditorFailure } from "./model";
import { localRescue, meetsReleaseGate, runPipeline } from "./pipeline";
import { resultApproval } from "./telemetry";

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
    assert.equal(unavailable.after.score, 99.9);
    assert.equal(unavailable.after.flaggedPhrases, 4);
    assert.match(unavailable.text, /thrilled to announce an update/);
    assert.match(unavailable.text, /This seamless experience empowers teams to unlock actionable insights\./);
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

test("a faithful Northstar feeling paraphrase is not a source rejection", async () => {
  const rewrite = localRescue(source).replace(
    "We’re thrilled to announce an update to Project Northstar.",
    "We feel thrilled about the update to Project Northstar.",
  );
  const oldFetch = globalThis.fetch;
  const oldWarn = console.warn;
  const logs: string[] = [];
  globalThis.fetch = (async () => Response.json({ rewrite, provider: "mock", model: "mock", stored: false, providerCalls: 1 })) as typeof fetch;
  console.warn = (value: string) => { logs.push(value); };
  try {
    const result = await runPipeline(env, { text: source, genre: "social", audience: "product managers" });
    assert.equal(result.text, rewrite);
    assert.equal(result.modelRequests, 1);
    assert.equal(result.factsPreserved, true);
    assert.doesNotMatch(result.note, /did not pass the source check|changed a source claim/);
    assert.ok(logs.every(value => JSON.parse(value).event !== "editor_source_rejected"));
    // This fixture still contains stock benefit wording. Source fidelity alone
    // must not turn it into an approved edit or lower the writing threshold.
    assert.equal(result.passedFinalChecks, false);
    assert.equal(result.status, "rewritten_with_warnings");
  } finally { globalThis.fetch = oldFetch; console.warn = oldWarn; }
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

test("provider attempt diagnostics retain bounded enums without exporting untrusted fields", async () => {
  const oldFetch = globalThis.fetch;
  const oldWarn = console.warn;
  const logs: string[] = [];
  console.warn = (value: string) => { logs.push(value); };
  try {
    for (const [providerAttempts, expected] of [
      [[{ provider: "workers-ai", outcome: "timeout", message: source },
        { provider: "openrouter", outcome: "unavailable", secret: signingKey }],
       [{ provider: "workers-ai", outcome: "timeout" }, { provider: "openrouter", outcome: "unavailable" }]],
      [[{ provider: "workers-ai", outcome: "unavailable", failureStage: "invoke", httpStatus: 401, message: source },
        { provider: "openrouter", outcome: "unavailable", failureStage: "http", httpStatus: 429, body: signingKey }],
       [{ provider: "workers-ai", outcome: "unavailable", failureStage: "invoke" },
        { provider: "openrouter", outcome: "unavailable", failureStage: "http", httpStatus: 429 }]],
      [[{ provider: source, outcome: signingKey }], []],
      [[{ provider: "workers-ai", outcome: "timeout" }, { provider: "openrouter", outcome: "unavailable" },
        { provider: "openrouter", outcome: "unavailable" }], []],
    ]) {
      globalThis.fetch = (async () => Response.json({ editorOutcome: "unavailable", providerCalls: 2, providerAttempts }, { status: 503 })) as typeof fetch;
      assert.equal(await callRole(env, "complete", source, {}, Date.now() + 1000), null);
      assert.deepEqual(JSON.parse(logs.at(-1)!).providerAttempts, expected);
    }
    assert.ok(logs.every(value => !value.includes(source) && !value.includes(signingKey)));
  } finally { globalThis.fetch = oldFetch; console.warn = oldWarn; }
});

test("provider failure metadata drops arbitrary stages and non-numeric or unobserved statuses", async () => {
  const oldFetch = globalThis.fetch;
  const oldWarn = console.warn;
  const logs: string[] = [];
  console.warn = (value: string) => { logs.push(value); };
  try {
    for (const [failureStage, httpStatus, expected] of [
      ["fetch", 503, { failureStage: "fetch" }],
      ["body", 200, { failureStage: "body", httpStatus: 200 }],
      ["http", 401, { failureStage: "http", httpStatus: 401 }],
      ["http", 403, { failureStage: "http", httpStatus: 403 }],
      ["http", 503, { failureStage: "http", httpStatus: 503 }],
      ["http", "429", { failureStage: "http" }],
      ["http", 429.5, { failureStage: "http" }],
      ["http", 99, { failureStage: "http" }],
      ["http", 600, { failureStage: "http" }],
      [source, 429, {}],
      [undefined, 429, {}],
    ] as const) {
      const providerAttempts = [{ provider: "openrouter", outcome: "unavailable", failureStage, httpStatus,
        message: source, body: signingKey, statusText: source, headers: { authorization: signingKey } }];
      globalThis.fetch = (async () => Response.json({ editorOutcome: "unavailable", providerCalls: 1, providerAttempts }, { status: 503 })) as typeof fetch;
      assert.equal(await callRole(env, "complete", source, {}, Date.now() + 1000), null);
      assert.deepEqual(JSON.parse(logs.at(-1)!).providerAttempts, [{ provider: "openrouter", outcome: "unavailable", ...expected }]);
    }
    assert.ok(logs.every(value => !value.includes(source) && !value.includes(signingKey)));
  } finally { globalThis.fetch = oldFetch; console.warn = oldWarn; }
});

test("successful provider records cannot carry failure metadata", async () => {
  const oldFetch = globalThis.fetch;
  const oldLog = console.log;
  const logs: string[] = [];
  console.log = (value: string) => { logs.push(value); };
  try {
    globalThis.fetch = (async () => Response.json({ rewrite: "A distinct edited draft.", provider: "mock", model: "mock", stored: false,
      providerCalls: 1, providerAttempts: [{ provider: "openrouter", outcome: "success", failureStage: "http", httpStatus: 503 }] })) as typeof fetch;
    assert.ok(await callRole(env, "complete", "An original draft.", {}, Date.now() + 1000));
    assert.deepEqual(JSON.parse(logs.at(-1)!).providerAttempts, [{ provider: "openrouter", outcome: "success" }]);
  } finally { globalThis.fetch = oldFetch; console.log = oldLog; }
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

test("a below-gate fallback is never advertised as a clean editorial rewrite", async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = (async () => Response.json({ error: "editor_unavailable", editorOutcome: "unavailable", providerCalls: 2 }, { status: 503 })) as typeof fetch;
  const lowScoreScorer = { fetch: async (url: RequestInfo | URL, init?: RequestInit) => {
    const response = await scorer.fetch(url, init);
    const payload = JSON.parse(String(init?.body));
    if (new URL(String(url)).pathname !== "/report" || payload.text === source) return response;
    const report = await response.json() as Record<string, unknown>;
    // Deliberately simulate the previous 20.2 result. Provenance and contextual
    // limits must still require review even if every measured check is green.
    return Response.json({ ...report, score: 20.2, band: "clear", highWeightFlags: 0,
      flaggedPhrases: 0, flags: [], readability: "clear", sentenceVariety: "natural",
      register: { measured: true, words: 50, checked: 4, findings: [], twoPartContrasts: 0, announcements: 0 },
      shape: { measured: true, broetry: false, oneSentenceParagraphShare: 0, longestFragmentRun: 0 } });
  } };
  try {
    const result = await runPipeline({ ...env, SCORER: lowScoreScorer } as unknown as Env, { text: source, genre: "social" });
    assert.equal(result.after.score, 20.2);
    assert.equal(meetsReleaseGate(result.after), true);
    assert.equal(result.factsPreserved, true);
    assert.equal(result.text, localRescue(source));
    assert.equal(result.status, "rewritten_with_warnings");
    assert.equal(result.passedFinalChecks, false);
    assert.equal(result.independentModelChecks, 0);
    assert.equal(result.rolesCompleted, 4);
    assert.equal(resultApproval(result), "review_required");
    assert.match(result.note, /local editor only removes stock wording; meaning, voice, and vague claims still need review/);
    assert.doesNotMatch(result.note, /approved|already reads cleanly/);
  } finally { globalThis.fetch = oldFetch; }
});
