import assert from "node:assert/strict";
import test from "node:test";
import { contextualReview } from "./contextual-review";
import { runPipeline } from "./pipeline";
import type { ContextualReview, WritingReport } from "./types";

const report: WritingReport = {
  score: 9.5, band: "clear", words: 12, sentences: 2, flaggedPhrases: 0,
  sentenceVariety: "natural", readability: "clear", highWeightFlags: 0,
  punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
  shape: { measured: false, broetry: false, oneSentenceParagraphShare: null, longestFragmentRun: null },
  register: { measured: false, words: 12, checked: 0, findings: [], twoPartContrasts: 0, announcements: 0 },
  flags: [],
};

function environment(): Env {
  return {
    EDITOR_ENDPOINT: "https://zero-slop.ai/api/demo-rewrite",
    EDITOR_SHARED_SECRET: "x".repeat(40), SCORER_VERSION: "test",
    SCORER: { fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input)).pathname;
      if (path === "/report") return Response.json(report);
      const body = JSON.parse(String(init?.body));
      const [name, text] = Object.entries(body.candidates as Record<string, string>)[0]!;
      return Response.json({ name, text, before: 9.5, after: 9.5, preserved: true, invented: false,
        ranked: [{ name, after: 9.5, preserved: true, invented: false }] });
    } },
  } as unknown as Env;
}

async function withReply(source: string, rewrite: string, review?: ContextualReview, providerCalls = 1) {
  const native = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
    calls++;
    const packet = JSON.parse(String(init?.body));
    assert.equal(packet.text, source);
    assert.equal(packet.noStore, true);
    assert.equal(packet.diagnostics.contextualReviewRequired, true);
    return Response.json({ rewrite, review, provider: "workers-ai", model: "fixture", stored: false, providerCalls });
  }) as typeof fetch;
  try {
    const result = await runPipeline(environment(), { text: source, genre: "professional" });
    return { result, calls };
  } finally { globalThis.fetch = native; }
}

test("review contract requires exact source evidence and consistent decisions", () => {
  const source = "The recommendation is the best choice.";
  const finding = { kind: "unsupported_claim", quote: "the best choice", reason: "No comparison basis is supplied.", question: "Which alternatives were compared?" };
  assert.deepEqual(contextualReview({ decision: "keep", findings: [] }, source, source), { decision: "keep", findings: [] });
  assert.ok(contextualReview({ decision: "gap", findings: [finding] }, source, source));
  for (const value of [
    { decision: "edit", findings: [] },
    { decision: "keep", findings: [finding] },
    { decision: "gap", findings: [{ ...finding, question: undefined }] },
    { decision: "gap", findings: [{ ...finding, quote: "invented evidence" }] },
    { decision: "gap", findings: [{ ...finding, kind: "probability" }] },
    { decision: "gap", findings: [{ ...finding, reason: "x".repeat(501) }] },
    { decision: "gap", findings: Array(9).fill(finding) },
    { decision: "gap", findings: [finding], probability: 0.99 },
  ]) assert.equal(contextualReview(value, source, source), null);
  assert.equal(contextualReview({ decision: "keep", findings: [] }, source, source + " Changed."), null);
  assert.equal(contextualReview({ decision: "gap", findings: [finding] }, source, "Different source."), null);
});

test("low-meter missing substance receives one request and preserves the source with a question", async () => {
  const source = "The recommendation is the best choice.";
  const review: ContextualReview = { decision: "gap", findings: [{ kind: "unsupported_claim", quote: "the best choice",
    reason: "No comparison basis is supplied.", question: "Which alternatives and criteria support this recommendation?" }] };
  const { result, calls } = await withReply(source, source, review);
  assert.equal(calls, 1);
  assert.equal(result.text, source);
  assert.equal(result.status, "unchanged_no_better_version");
  assert.equal(result.passedFinalChecks, false);
  assert.equal(result.independentModelChecks, 0);
  assert.deepEqual(result.contextualReview, { status: "reviewed", ...review });
  assert.equal(result.modelRequests, 1);
  assert.match(result.note, /Which alternatives and criteria support this recommendation\?/);
});

test("reviewed keep retains informal voice verbatim without an alternate request", async () => {
  const source = "lmk when the cache is warm. i'm leaving the retries alone.";
  const { result, calls } = await withReply(source, source, { decision: "keep", findings: [] });
  assert.equal(calls, 1);
  assert.equal(result.text, source);
  assert.equal(result.status, "already_clear");
  assert.equal(result.modelRequests, 1);
  assert.equal(result.passedFinalChecks, false);
  assert.equal(result.independentModelChecks, 0);
});

test("grounded equal-score edits remain eligible after source and claim checks", async () => {
  const source = "The report summarizes totals. Its summary summarizes totals.";
  const rewrite = "The report summarizes totals.";
  const review: ContextualReview = { decision: "edit", findings: [{ kind: "redundancy", quote: "Its summary summarizes totals.", reason: "The second sentence repeats the first." }] };
  const { result, calls } = await withReply(source, rewrite, review);
  assert.equal(calls, 1);
  assert.equal(result.text, rewrite);
  assert.equal(result.before.score, result.after.score);
  assert.equal(result.status, "rewritten");
  assert.equal(result.passedFinalChecks, true);
  assert.equal(result.independentModelChecks, 0);
});

test("a bare echo is unreviewed and never silently certified clean", async () => {
  const source = "The request contains the request details.";
  const { result } = await withReply(source, source);
  assert.equal(result.text, source);
  assert.equal(result.status, "unchanged_service_unavailable");
  assert.deepEqual(result.contextualReview, { status: "unavailable" });
  assert.equal(result.passedFinalChecks, false);
});

test("invalid evidence cannot ship a proposal or lose the observed attempt count", async () => {
  const source = "The request contains the request details.";
  const review = { decision: "edit", findings: [{ kind: "style", quote: "absent evidence", reason: "An unsupported diagnosis." }] } as ContextualReview;
  const { result } = await withReply(source, "The request includes a new guarantee.", review, 2);
  assert.equal(result.text, source);
  assert.equal(result.status, "unchanged_service_unavailable");
  assert.equal(result.modelRequests, 2);
  assert.equal(result.passedFinalChecks, false);
});


test("review bounds count Unicode code points consistently with the public contract", () => {
  const quote = "😀".repeat(400);
  const review = { decision: "edit", findings: [{ kind: "style", quote, reason: "Clearer punctuation." }] };
  assert.ok(contextualReview(review, quote, quote + "."));
  assert.equal(contextualReview({ ...review, findings: [{ ...review.findings[0], quote: quote + "😀" }] }, quote + "😀", "Changed."), null);
});

test("a grounded diagnosis cannot override existing source-claim guards", async () => {
  const source = "We do not store drafts.";
  const rewrite = "We store drafts.";
  const review: ContextualReview = { decision: "edit", findings: [{ kind: "style", quote: "do not", reason: "A claimed style improvement." }] };
  const { result } = await withReply(source, rewrite, review);
  assert.equal(result.passedFinalChecks, false);
  assert.equal(result.factsPreserved, true);
  assert.equal(result.text, source);
  assert.equal(result.status, "unchanged_verification_failed");
  assert.match(result.note, /source claim/);
});


test("a reviewed modality upgrade cannot replace Unicode source identifiers or certainty", async () => {
  const source = "Zoë’s 東京 pilot may be viable. Ticket ABC-2048 belongs to Łukasz.";
  const rewrite = source.replace("may be", "is");
  const review: ContextualReview = { decision: "edit", findings: [{ kind: "style", quote: "may be viable", reason: "A claimed simplification." }] };
  const { result } = await withReply(source, rewrite, review);
  assert.equal(result.text, source);
  assert.equal(result.status, "unchanged_verification_failed");
  assert.equal(result.factsPreserved, true);
  assert.equal(result.passedFinalChecks, false);
  assert.deepEqual(result.contextualReview, { status: "reviewed", ...review });
});
