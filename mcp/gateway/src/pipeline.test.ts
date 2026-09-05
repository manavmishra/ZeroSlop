import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { callRole, editorReply, signedEditorHeaders, tooLong, tooShort } from "./model";
import { localRescue, runPipeline, scorerGuidance } from "./pipeline";
import type { WritingReport } from "./types";

const rescueScript = fileURLToPath(new URL("../../../scripts/rescue.py", import.meta.url));

function signingKeyForTests(): string {
  return Array.from({ length: 40 }, (_, index) => String.fromCharCode(97 + (index % 26))).join("");
}

function writingReport(score: number, overrides: Partial<WritingReport> = {}): WritingReport {
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
    ...overrides,
  };
}

function scorerHarness(original: string, rewrite: string, afterScore = 9.5, modelUnsafe = false) {
  return {
    fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      if (url.pathname === "/report") {
        return Response.json(writingReport(body.text === original ? 91 : afterScore));
      }
      if (url.pathname === "/delta") {
        return Response.json({ original_words: 20, rewrite_words: 10, net: -10, inserted_runs: [], deleted_runs: [], cut_emphasis: [] });
      }
      const entries = Object.entries(body.candidates as Record<string, string>);
      const safeEntries = entries.filter(([name]) => !(modelUnsafe && name === "one-call edit"));
      const [name, text] = safeEntries[0] ?? entries[0] ?? ["none", original];
      return Response.json({
        name,
        text,
        preserved: !(modelUnsafe && name === "one-call edit"),
        invented: modelUnsafe && name === "one-call edit",
        before: 91,
        after: text === original ? 91 : afterScore,
        ranked: entries.map(([candidate, value]) => ({
          name: candidate,
          after: value === original ? 91 : afterScore,
          preserved: !(modelUnsafe && candidate === "one-call edit"),
          invented: modelUnsafe && candidate === "one-call edit",
        })),
      });
    },
  };
}

test("editor response requires a confirmed no-store path", () => {
  assert.deepEqual(
    editorReply({ rewrite: "  edited  ", provider: "router", model: "writer", stored: false }),
    { text: "edited", rung: "router:writer" },
  );
  assert.equal(editorReply({ rewrite: "edited", provider: "router", model: "writer" }), null);
  assert.equal(editorReply({ rewrite: "edited", provider: "router", model: "writer", stored: true }), null);
  assert.equal(editorReply({ rewrite: "edited", provider: "router\nspoof", model: "writer", stored: false }), null);
});

test("complete editor output has bounded length", () => {
  assert.equal(tooShort("one two three four five six seven eight nine ten", "one", "complete"), true);
  assert.equal(tooShort("one two", "one two", "complete"), false);
  assert.equal(tooLong("short source", "x".repeat(1_001), "complete"), true);
  assert.equal(tooLong("x".repeat(20_000), "x".repeat(30_000), "complete"), false);
});

test("scorer guidance is bounded and gives the editor exact targets", () => {
  const report = writingReport(88);
  report.flags = Array.from({ length: 20 }, (_, index) => ({
    phrase: `flag ${index}`, strength: 4, issue: "stock phrase", direction: "cut it",
  }));
  const guidance = JSON.parse(scorerGuidance(report));
  assert.equal(guidance.target, "below 25");
  assert.equal(guidance.flaggedPhrases.length, 12);
});

test("editor requests are signed without exposing the secret", async () => {
  const signingKey = signingKeyForTests();
  const headers = await signedEditorHeaders(signingKey, '{"role":"complete"}', 1_700_000_000_000);
  assert.equal(headers["x-zero-slop-timestamp"], "1700000000000");
  assert.match(headers["x-zero-slop-signature"] ?? "", /^[0-9a-f]{64}$/);
  assert.ok(!Object.values(headers).includes(signingKey));
  await assert.rejects(Reflect.apply(signedEditorHeaders, undefined, [undefined, "body"]), /editor_secret_unavailable/);
  await assert.rejects(signedEditorHeaders("short", "body"), /editor_secret_unavailable/);
});

test("callRole makes one bounded, no-store, non-redirecting request", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  let captured: RequestInit | undefined;
  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
    calls += 1;
    captured = init;
    return Response.json({ rewrite: "Edited draft with enough words to be a complete and useful response.", provider: "workers-ai", model: "editor", stored: false });
  }) as typeof fetch;
  try {
    const source = "Original draft with enough words to be a complete and useful source for editing.";
    const reply = await callRole({
      EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite",
      EDITOR_SHARED_SECRET: signingKeyForTests(),
    } as unknown as Env, "complete", source, { genre: "general" }, Date.now() + 5_000);
    assert.ok(reply);
    assert.equal(calls, 1);
    assert.equal(captured?.redirect, "manual");
    const body = JSON.parse(String(captured?.body));
    assert.equal(body.role, "complete");
    assert.equal(body.noStore, true);
    assert.equal(body.text, source);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("an expired editor deadline makes no request", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = (async () => { calls += 1; return new Response(); }) as typeof fetch;
  try {
    const result = await callRole({} as Env, "complete", "Draft", {}, Date.now() - 1);
    assert.equal(result, null);
    assert.equal(calls, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("clean text exits after scoring without a model request", async () => {
  const scorer = { fetch: async () => Response.json(writingReport(9.5)) };
  const result = await runPipeline({ SCORER: scorer, SCORER_VERSION: "2.8.11" } as unknown as Env,
    { text: "The importer now maps CSV headers automatically.", genre: "general" });
  assert.equal(result.status, "already_clear");
  assert.equal(result.modelRequests, 0);
  assert.equal(result.rolesCompleted, 1);
});

test("the complete MCP edit uses one remote model request", async () => {
  const original = "We are incredibly excited to share that Kairoset 4.0 marks a transformative milestone for our journey.";
  const rewrite = "Kairoset 4.0 is available to the team.";
  let editorRequests = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
    editorRequests += 1;
    const body = JSON.parse(String(init?.body)) as { role?: string };
    assert.equal(body.role, "complete");
    return Response.json({ rewrite, provider: "workers-ai", model: "editor", stored: false });
  }) as typeof fetch;
  try {
    const result = await runPipeline({
      SCORER: scorerHarness(original, rewrite), SCORER_VERSION: "2.8.11",
      EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite", EDITOR_SHARED_SECRET: signingKeyForTests(),
    } as unknown as Env, { text: original, genre: "general" });
    assert.equal(editorRequests, 1);
    assert.equal(result.modelRequests, 1);
    assert.equal(result.text, rewrite);
    assert.equal(result.status, "rewritten");
    assert.equal(result.rolesCompleted, 8);
    assert.equal(result.finishingRounds, 1);
    assert.equal(result.independentModelChecks, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("a model outage still returns a changed local edit after one request", async () => {
  const original = "We are incredibly excited to share some news about our journey with Kairoset over 18 months.";
  const local = localRescue(original);
  let requests = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => { requests += 1; return Response.json({ error: "busy" }, { status: 503 }); }) as typeof fetch;
  try {
    const result = await runPipeline({
      SCORER: scorerHarness(original, local, 18), SCORER_VERSION: "2.8.11",
      EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite", EDITOR_SHARED_SECRET: signingKeyForTests(),
    } as unknown as Env, { text: original, genre: "social" });
    assert.equal(requests, 1);
    assert.notEqual(result.text, original);
    assert.equal(result.text, local);
    assert.equal(result.status, "rewritten_with_warnings");
    assert.equal(result.factsPreserved, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("an unsafe model response loses to the local source-safe edit", async () => {
  const original = "We are incredibly excited to share some news about our journey with Kairoset over 18 months.";
  const invented = "Kairoset doubled revenue over 18 months.";
  const local = localRescue(original);
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => Response.json({ rewrite: invented, provider: "workers-ai", model: "editor", stored: false })) as typeof fetch;
  try {
    const result = await runPipeline({
      SCORER: scorerHarness(original, local, 18, true), SCORER_VERSION: "2.8.11",
      EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite", EDITOR_SHARED_SECRET: signingKeyForTests(),
    } as unknown as Env, { text: original, genre: "social" });
    assert.equal(result.text, local);
    assert.doesNotMatch(result.text, /doubled revenue/);
    assert.equal(result.factsPreserved, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("local fallback preserves the launch fixture's protected details", () => {
  const input = "We are incredibly excited to share some news about our journey over the past 18 months. " +
    "Our team spoke to 40 customers. The real win was not the time saved. It was watching Kairoset move " +
    "from day nine to day two while keeping its 4.8 score and serving 200 teams.";
  const output = localRescue(input);
  assert.notEqual(output, input);
  assert.doesNotMatch(output, /incredibly excited|excited to share|our journey/i);
  assert.ok(output.includes("The real win was not the time saved."));
  for (const detail of ["18", "40", "Kairoset", "day nine", "day two", "4.8", "200"]) {
    assert.ok(output.includes(detail), `lost ${detail}`);
  }
  assert.equal(localRescue("We're excited to share some news about the release."), "We're excited about the release.");
  assert.equal(
    localRescue("Kairoset 4.0 redefines what's possible in onboarding automation."),
    "Kairoset 4.0 updates onboarding automation.",
  );
  assert.equal(
    localRescue("We’re excited to share what’s happened. Onboarding isn’t a checklist—it’s a promise."),
    "We're excited about what’s happened. We see onboarding as a promise.",
  );
  assert.equal(
    localRescue(
      "We are incredibly excited to share our transformative journey. " +
      "The results speak for themselves: setup time is down 73 percent for Kairoset.",
    ),
    "We're sharing our work. Setup time is down 73 percent for Kairoset.",
  );
  assert.equal(
    localRescue("Our cutting‑edge editor handles 50 000 words."),
    "Our editor handles 50 000 words.",
  );
});

test("local fallback never rewrites quotations, code, or links", () => {
  const input = [
    "We are incredibly excited to share some news about the release.",
    'The customer wrote, "We are incredibly excited to share about Kairoset."',
    "Keep `we are incredibly excited to share about` as the exact test fixture.",
    "See [our journey](https://example.com/our-journey) and https://example.com/we-are-incredibly-excited.",
  ].join("\n\n");
  const output = localRescue(input);
  assert.match(output, /^We're excited about the release\./);
  assert.ok(output.includes('"We are incredibly excited to share about Kairoset."'));
  assert.ok(output.includes("`we are incredibly excited to share about`"));
  assert.ok(output.includes("[our journey](https://example.com/our-journey)"));
  assert.ok(output.includes("https://example.com/we-are-incredibly-excited."));
});

test("local fallback fully cleans the public release fixture", () => {
  const input = "We are thrilled to unveil Kairoset 4.0, a transformative release that redefines what is possible in onboarding automation.\n\n" +
    "This release represents a significant milestone in our journey to empower teams everywhere. We have listened carefully to your feedback and are excited to deliver a suite of powerful new capabilities.\n\n" +
    "Our cutting-edge mapping engine now automatically detects and maps fields across your connected systems, eliminating hours of tedious manual configuration.\n\n" +
    "We have completely reimagined our search infrastructure, delivering results up to 40 times faster than before.\n\n" +
    "Bulk export now handles up to 50000 records in a single operation, with robust error handling built in from the ground up.\n\n" +
    "Audit logs give full visibility into every change, with 90 days of retention on all plans.\n\n" +
    "We believe these improvements will fundamentally transform how your team works, and the release is available today.";
  const output = localRescue(input);
  assert.equal(output, "Kairoset 4.0 updates onboarding automation.\n\n" +
    "We listened to your feedback and added new capabilities.\n\n" +
    "Our mapping engine now automatically detects and maps fields across your connected systems, eliminating hours of manual configuration.\n\n" +
    "We rebuilt our search infrastructure, delivering results up to 40 times faster than before.\n\n" +
    "Bulk export now handles up to 50000 records in a single operation, with built-in error handling.\n\n" +
    "Audit logs give full visibility into every change, with 90 days of retention on all plans.\n\n" +
    "The release is available today.");
});

test("gateway fallback matches the installed skill byte for byte", () => {
  const samples = [
    "We are incredibly excited to share our transformative journey. The results speak for themselves: setup time is down 73 percent for Kairoset.",
    "Our cutting‑edge editor handles 50 000 words.",
    'The customer wrote, "We are incredibly excited to share about Kairoset." See [our journey](https://example.com/our-journey).',
    "The update is available today. Search is up to 40 times faster.",
    "It is important to note that the release is ready. It is worth noting that iOS is supported.",
    "Our two tools seamlessly integrate. The agent seamlessly integrates with the queue.",
    "The real win was not the money. It was the time saved.",
    "It is worth noting that we are keeping the review. At the end of the day, Maya approves it.",
    "We are ready. It is available. They are waiting. We did not change the deadline.",
    "We are leveraging automation to unlock the full potential of our team.",
  ];
  for (const source of samples) {
    const installed = execFileSync("python3", [rescueScript, "-"], {
      input: source,
      encoding: "utf8",
    }).trimEnd();
    assert.equal(localRescue(source), installed);
  }
});
