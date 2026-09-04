import assert from "node:assert/strict";
import test from "node:test";

import { callRole, editorReply, signedEditorHeaders, tooLong, tooShort } from "./model";
import {
  releaseReady,
  runPipeline,
  scorerGuidance,
  verifierPassed,
} from "./pipeline";
import type { RankedRewrite, WritingReport } from "./types";

function signingKeyForTests(): string {
  return Array.from({ length: 40 }, (_, index) => String.fromCharCode(97 + (index % 26))).join("");
}

test("verifier accepts only the exact success token", () => {
  assert.equal(verifierPassed("OK"), true);
  assert.equal(verifierPassed("OK."), true);
  assert.equal(verifierPassed("Mostly OK"), false);
  assert.equal(verifierPassed(null), false);
});

test("release gate requires source safety, clean document checks, two verdicts, and score", () => {
  const checked = { preserved: true, invented: false, after: 12 } as RankedRewrite;
  const report = {
    register: { findings: [] },
    shape: { broetry: false },
  } as unknown as WritingReport;
  assert.equal(releaseReady(checked, report, ["OK", "OK."], ["a", "b"]), true);
  assert.equal(releaseReady({ ...checked, invented: true }, report, ["OK", "OK"], ["a", "b"]), false);
  assert.equal(releaseReady({ ...checked, after: 25 }, report, ["OK", "OK"], ["a", "b"]), false);
  assert.equal(releaseReady(checked, { ...report, shape: { ...report.shape, broetry: true } }, ["OK", "OK"], ["a", "b"]), false);
  assert.equal(releaseReady(checked, report, ["OK", "BLOCK: changed scope"], ["a", "b"]), false);
  assert.equal(releaseReady(checked, report, ["OK", "OK"], ["same", "same"]), false);
});

test("editor response requires a confirmed no-store path", () => {
  assert.deepEqual(
    editorReply({ rewrite: "  edited  ", provider: "router", model: "writer", stored: false }),
    { text: "edited", rung: "router:writer" },
  );
  assert.equal(editorReply({ rewrite: "edited", provider: "router", model: "writer" }), null);
  assert.equal(editorReply({ rewrite: "edited", provider: "router", model: "writer", stored: true }), null);
  assert.equal(editorReply({ rewrite: "edited", provider: "router\nspoof", model: "writer", stored: false }), null);
  assert.equal(editorReply({ rewrite: "edited", provider: "r".repeat(121), model: "writer", stored: false }), null);
  assert.equal(editorReply({}), null);
});

test("truncation guard rejects implausibly short prose", () => {
  assert.equal(tooShort("one two three four", "one", "rewrite_strip"), true);
  assert.equal(tooShort("one two", "one two", "copydesk"), false);
  const hollow = Array.from({ length: 80 }, (_, index) => `word${index}`).join(" ");
  const factualCore = Array.from({ length: 18 }, (_, index) => `fact${index}`).join(" ");
  assert.equal(tooShort(hollow, factualCore, "rewrite_strip"), false);
  assert.equal(tooShort(hollow, factualCore, "copydesk"), true);
});

test("expansion guard bounds every editor role", () => {
  assert.equal(tooLong("short source", "x".repeat(1_001), "copydesk"), true);
  assert.equal(tooLong("short source", "x".repeat(201), "verify"), true);
  assert.equal(tooLong("short source", "OK", "verify"), false);
  assert.equal(tooLong("x".repeat(20_000), "x".repeat(30_000), "rewrite_strip"), false);
  assert.equal(tooLong("x".repeat(20_000), "x".repeat(40_001), "rewrite_strip"), true);
});

test("scorer guidance is bounded and gives rewriters exact targets", () => {
  const report = writingReport(88);
  report.flags = Array.from({ length: 20 }, (_, index) => ({
    phrase: `flag ${index}`,
    strength: 4,
    issue: "stock phrase",
    direction: "cut it",
  }));
  report.register.findings = Array.from({ length: 8 }, (_, index) => ({
    name: `finding ${index}`,
    rate: 5,
    budget: 2,
    found: 1,
    quote: `quote ${index}`,
  }));
  const guidance = JSON.parse(scorerGuidance(report));
  assert.equal(guidance.target, "below 25");
  assert.equal(guidance.flaggedPhrases.length, 12);
  assert.equal(guidance.registerFindings.length, 4);
  assert.equal(guidance.flaggedPhrases[0].phrase, "flag 0");
});

test("editor requests are signed without exposing the shared secret", async () => {
  const signingKey = signingKeyForTests();
  const headers = await signedEditorHeaders(
    signingKey,
    '{"role":"verify"}',
    1_700_000_000_000,
  );
  assert.equal(headers["x-zero-slop-timestamp"], "1700000000000");
  assert.match(headers["x-zero-slop-signature"] ?? "", /^[0-9a-f]{64}$/);
  assert.ok(!Object.values(headers).includes(signingKey));
});

test("editor calls refuse redirects and reject oversized responses", async () => {
  const originalFetch = globalThis.fetch;
  let redirect: RequestRedirect | undefined;
  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
    redirect = init?.redirect;
    return Response.json({ rewrite: "Edited draft.", provider: "router", model: "editor", stored: false });
  }) as typeof fetch;
  const env = {
    EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite",
    EDITOR_SHARED_SECRET: signingKeyForTests(),
  } as unknown as Env;
  try {
    const reply = await callRole(env, "copydesk", "Draft.", "Draft.", Date.now() + 5_000);
    assert.equal(reply?.text, "Edited draft.");
    assert.equal(redirect, "error");

    globalThis.fetch = (async () => Response.json({
      rewrite: "x".repeat(300_000),
      provider: "router",
      model: "editor",
      stored: false,
    })) as typeof fetch;
    assert.equal(await callRole(env, "copydesk", "Draft.", "Draft.", Date.now() + 5_000), null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

function writingReport(score: number): WritingReport {
  return {
    score,
    band: score < 25 ? "clear" : "rewrite",
    words: 30,
    sentences: 2,
    flaggedPhrases: score < 25 ? 0 : 9,
    sentenceVariety: "natural",
    readability: "clear",
    punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
    highWeightFlags: score < 25 ? 0 : 5,
    shape: { measured: true, broetry: false, oneSentenceParagraphShare: 0, longestFragmentRun: 0 },
    register: { measured: true, words: 30, checked: 4, findings: [], twoPartContrasts: 0, announcements: 0 },
    flags: [],
  };
}

test("clean text exits after scoring and never reaches an editor", async () => {
  const scorer = {
    fetch: async () => Response.json({
      ...writingReport(9.5),
      register: { ...writingReport(9.5).register, measured: true, words: 320 },
    }),
  };
  const result = await runPipeline({
    SCORER: scorer,
    SCORER_VERSION: "2.8.7",
  } as unknown as Env, { text: "The importer now maps CSV headers automatically.", genre: "general" });

  assert.equal(result.status, "already_clear");
  assert.equal(result.before.score, 9.5);
  assert.equal(result.after.score, 9.5);
  assert.equal(result.rolesCompleted, 1);
});

test("a short low-scoring draft still gets the checks that abstained", async () => {
  const originalFetch = globalThis.fetch;
  let editorCalls = 0;
  const editorRoles: string[] = [];
  const scorer = {
    fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      if (url.pathname === "/report") return Response.json({
        ...writingReport(9.5),
        register: { ...writingReport(9.5).register, measured: false, words: 7 },
      });
      if (url.pathname === "/delta") return Response.json({ original_words: 7, rewrite_words: 7, net: 0, inserted_runs: [], deleted_runs: [], cut_emphasis: [] });
      const [name, text] = Object.entries(body.candidates as Record<string, string>)[0]
        ?? ["source", body.original];
      return Response.json({ name, text, preserved: true, invented: false, before: 9.5, after: 9.5, ranked: [] });
    },
  };
  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
    editorCalls += 1;
    const body = JSON.parse(String(init?.body)) as { role?: unknown };
    editorRoles.push(String(body.role));
    return Response.json({ rewrite: "OK", provider: "router", model: "editor", stored: false });
  }) as typeof fetch;
  try {
    const result = await runPipeline({
      SCORER: scorer,
      SCORER_VERSION: "2.8.7",
      EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite",
      EDITOR_SHARED_SECRET: signingKeyForTests(),
    } as unknown as Env, { text: "The importer now maps CSV headers automatically.", genre: "general" });
    assert.notEqual(result.rolesCompleted, 1);
    assert.equal(result.status, "unchanged_service_unavailable");
    assert.equal(result.rolesCompleted, 2, "failed model stages must not be reported as completed");
    assert.ok(editorCalls > 0);
    assert.equal(editorRoles.filter((role) => role.startsWith("rewrite_")).length, 4,
      "a first-round outage must use the remaining bounded rewrite attempts");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("full pipeline releases only a no-store rewrite with two independent verifiers", async () => {
  const original = "Harbor 4.0 is now available, and it is important to note that search is now up to 40x faster; in addition, bulk export supports 50,000 records; furthermore, audit logs retain every change for 90 days on every plan. In conclusion, Harbor 4.0 is now available.";
  const rewrite = "Harbor 4.0 is now available. Search is now up to 40x faster, bulk export supports 50,000 records, and audit logs retain every change for 90 days on every plan.";
  const editorCalls: Array<Record<string, unknown>> = [];
  const originalFetch = globalThis.fetch;
  let interpreterAvailable = true;

  const scorer = {
    fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      if (url.pathname === "/report") {
        return Response.json(writingReport(body.text === original ? 97.5 : 9.5));
      }
      if (url.pathname === "/delta") {
        return Response.json({
          original_words: 41,
          rewrite_words: 26,
          net: -15,
          inserted_runs: [],
          deleted_runs: [],
          cut_emphasis: [],
        });
      }
      const entries = Object.entries(body.candidates as Record<string, string>);
      const [name, text] = entries.find(([candidate]) => candidate !== "your draft")
        ?? ["source", original];
      return Response.json({
        name,
        text,
        preserved: true,
        invented: false,
        before: 97.5,
        after: text === original ? 97.5 : 9.5,
        ranked: entries.map(([candidate, value]) => ({
          name: candidate,
          after: value === original ? 97.5 : 9.5,
          preserved: true,
          invented: false,
        })),
      });
    },
  };

  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    editorCalls.push(body);
    const role = String(body.role);
    if (role === "interpret") {
      if (!interpreterAvailable) return Response.json({ error: "unavailable" }, { status: 503 });
      return Response.json({ rewrite: "Keep Harbor 4.0 and every figure.", provider: "router", model: "notes", stored: false });
    }
    if (role === "verify") {
      const strict = body.strictExclude === true;
      return Response.json({ rewrite: "OK", provider: "router", model: strict ? "verify-b" : "verify-a", stored: false });
    }
    return Response.json({ rewrite, provider: "router", model: role, stored: false });
  }) as typeof fetch;

  try {
    const result = await runPipeline({
      SCORER: scorer,
      SCORER_VERSION: "2.8.7",
      EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite",
      EDITOR_SHARED_SECRET: signingKeyForTests(),
    } as unknown as Env, { text: original, genre: "general" });

    assert.equal(result.status, "rewritten");
    assert.equal(result.text, rewrite);
    assert.equal(result.before.score, 97.5);
    assert.equal(result.after.score, 9.5);
    assert.equal(result.independentModelChecks, 2);
    assert.equal(result.passedFinalChecks, true);
    assert.equal(result.rolesCompleted, 8);
    assert.ok(editorCalls.every((call) => call.noStore === true));
    const rewrites = editorCalls.filter((call) => String(call.role).startsWith("rewrite_"));
    assert.ok(rewrites.every((call) => call.strictExclude === false));
    const verifiers = editorCalls.filter((call) => call.role === "verify");
    assert.equal(verifiers.length, 2);
    const secondVerifier = verifiers[1];
    assert.ok(secondVerifier);
    assert.equal(secondVerifier.strictExclude, true);
    assert.deepEqual(secondVerifier.exclude, ["router:verify-a"]);

    interpreterAvailable = false;
    const withoutInterpreter = await runPipeline({
      SCORER: scorer,
      SCORER_VERSION: "2.8.7",
      EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite",
      EDITOR_SHARED_SECRET: signingKeyForTests(),
    } as unknown as Env, { text: original, genre: "general" });
    assert.equal(withoutInterpreter.status, "rewritten");
    assert.equal(withoutInterpreter.rolesCompleted, 7,
      "a successful run must not claim that an unavailable interpreter completed");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

async function runWarningScenario(
  afterScore: number,
  secondVerdict: string,
  preferSourceOnMixedRank = false,
) {
  const original = "Harbor 4.0 is now available, and it is important to note that search is now up to 40x faster. In conclusion, Harbor 4.0 is now available.";
  const rewrite = "Harbor 4.0 is now available. Search is now up to 40x faster.";
  const originalFetch = globalThis.fetch;
  const scorer = {
    fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      if (url.pathname === "/report") {
        return Response.json(writingReport(body.text === original ? 88 : afterScore));
      }
      if (url.pathname === "/delta") {
        return Response.json({
          original_words: 27,
          rewrite_words: 12,
          net: -15,
          inserted_runs: [],
          deleted_runs: [],
          cut_emphasis: [],
        });
      }
      const entries = Object.entries(body.candidates as Record<string, string>);
      const [name, text] = (preferSourceOnMixedRank && entries.length > 1
        ? entries.find(([candidate]) => candidate === "your draft")
        : entries.find(([, value]) => value === rewrite))
        ?? entries[0]
        ?? ["source", original];
      return Response.json({
        name,
        text,
        preserved: true,
        invented: false,
        before: 88,
        after: text === original ? 88 : afterScore,
        ranked: entries.map(([candidate, value]) => ({
          name: candidate,
          after: value === original ? 88 : afterScore,
          preserved: true,
          invented: false,
        })),
      });
    },
  };
  let verifierCalls = 0;
  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    const role = String(body.role);
    if (role === "interpret") {
      return Response.json({ rewrite: "Keep Harbor 4.0 and 40x.", provider: "router", model: "notes", stored: false });
    }
    if (role === "verify") {
      verifierCalls += 1;
      return Response.json({
        rewrite: verifierCalls % 2 === 0 ? secondVerdict : "OK",
        provider: "router",
        model: verifierCalls % 2 === 0 ? "verify-b" : "verify-a",
        stored: false,
      });
    }
    return Response.json({ rewrite, provider: "router", model: role, stored: false });
  }) as typeof fetch;

  try {
    return await runPipeline({
      SCORER: scorer,
      SCORER_VERSION: "2.8.7",
      EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite",
      EDITOR_SHARED_SECRET: signingKeyForTests(),
    } as unknown as Env, { text: original, genre: "general" });
  } finally {
    globalThis.fetch = originalFetch;
  }
}

test("a verifier warning returns the safe edit instead of suppressing it", async () => {
  const result = await runWarningScenario(14.5, "BLOCK: cadence still feels repetitive");
  assert.equal(result.status, "rewritten_with_warnings");
  assert.equal(result.text, "Harbor 4.0 is now available. Search is now up to 40x faster.");
  assert.equal(result.after.score, 14.5);
  assert.equal(result.factsPreserved, true);
  assert.equal(result.passedFinalChecks, false);
});

test("missing the score target returns the safe edit with a warning", async () => {
  const result = await runWarningScenario(31, "OK");
  assert.equal(result.status, "rewritten_with_warnings");
  assert.equal(result.text, "Harbor 4.0 is now available. Search is now up to 40x faster.");
  assert.equal(result.after.score, 31);
  assert.equal(result.factsPreserved, true);
  assert.equal(result.passedFinalChecks, false);
});

test("an editorial preference for the source cannot suppress a safe changed draft", async () => {
  const result = await runWarningScenario(31, "OK", true);
  assert.equal(result.status, "rewritten_with_warnings");
  assert.equal(result.text, "Harbor 4.0 is now available. Search is now up to 40x faster.");
  assert.equal(result.factsPreserved, true);
});
