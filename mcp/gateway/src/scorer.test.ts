import assert from "node:assert/strict";
import test from "node:test";

import { inventoryChanges, rankRewrites, scoreWriting, scorerHealth } from "./scorer";

function scorerEnv(payload: unknown, status = 200): Env {
  return {
    SCORER: {
      async fetch() {
        return Response.json(payload, { status });
      },
    },
  } as unknown as Env;
}

function validReport() {
  return {
    score: 12.5,
    band: "clear",
    words: 12,
    sentences: 2,
    flaggedPhrases: 0,
    sentenceVariety: "natural",
    readability: "clear",
    punctuation: { dashes: 0, emoji: 0, hashtags: 0 },
    highWeightFlags: 0,
    shape: {
      measured: true,
      broetry: false,
      oneSentenceParagraphShare: 0.5,
      longestFragmentRun: 0,
    },
    register: {
      measured: true,
      words: 12,
      checked: 4,
      findings: [],
      twoPartContrasts: 0,
      announcements: 0,
    },
    flags: [],
  };
}

test("accepts a complete writing report from the private scorer", async () => {
  const report = await scoreWriting(scorerEnv(validReport()), "A complete draft.", "general");
  assert.equal(report.score, 12.5);
  assert.equal(report.shape.measured, true);
});

test("rejects incomplete or impossible writing reports at the service boundary", async () => {
  await assert.rejects(
    scoreWriting(scorerEnv({ score: 12.5 }), "A complete draft.", "general"),
    /scorer_invalid_response/,
  );
  await assert.rejects(
    scoreWriting(scorerEnv({ ...validReport(), score: 101 }), "A complete draft.", "general"),
    /scorer_invalid_response/,
  );
});

test("validates ranking and change-inventory payloads", async () => {
  const ranked = await rankRewrites(scorerEnv({
    name: "candidate",
    text: "Edited draft.",
    preserved: true,
    invented: false,
    before: 50,
    after: 10,
    ranked: [{ name: "candidate", after: 10, preserved: true, invented: false }],
  }), "Original draft.", { candidate: "Edited draft." }, "general");
  assert.equal(ranked.after, 10);

  const changes = await inventoryChanges(scorerEnv({
    original_words: 2,
    rewrite_words: 2,
    net: 0,
    inserted_runs: ["Edited"],
    deleted_runs: ["Original"],
    cut_emphasis: [],
  }), "Original draft.", "Edited draft.");
  assert.equal(changes.net, 0);

  await assert.rejects(
    inventoryChanges(scorerEnv({ original_words: -1 }), "Original draft.", "Edited draft."),
    /scorer_invalid_response/,
  );
});

test("validates health payloads instead of trusting the service binding", async () => {
  assert.deepEqual(
    await scorerHealth(scorerEnv({ ok: true, scorerVersion: "2.8.9" })),
    { ok: true, scorerVersion: "2.8.9" },
  );
  await assert.rejects(
    scorerHealth(scorerEnv({ ok: "yes", scorerVersion: "2.8.9" })),
    /scorer_invalid_response/,
  );
  await assert.rejects(
    scorerHealth(scorerEnv({ error: "down" }, 503)),
    /scorer_503/,
  );
});
