import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

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

test("the real Python scorer satisfies the gateway contract for punctuation and protected Markdown", async () => {
  const source = [
    "# Release instructions",
    "It is important to note that Maya owns pricing — Omar owns the review.",
    "Run `deploy --dry-run` first.",
    '```sh\necho "leverage the synergy"\n```',
    "Read [the checklist](https://example.com/release?version=4.2).",
  ].join("\n\n");
  const payload = JSON.parse(execFileSync("python3", [
    "-c",
    "import sys,json;sys.path.insert(0,sys.argv[1]);import scorer_core;print(json.dumps(scorer_core.report(sys.stdin.read(),'professional')))",
    fileURLToPath(new URL("../../scorer/src", import.meta.url)),
  ], { input: source, encoding: "utf8" }));
  const report = await scoreWriting(scorerEnv(payload), source, "professional");
  assert.equal(report.punctuation.dashes, 2);
  assert.ok(report.flags.length > 0);
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
    await scorerHealth(scorerEnv({ ok: true, scorerVersion: "2.9.0" })),
    { ok: true, scorerVersion: "2.9.0" },
  );
  await assert.rejects(
    scorerHealth(scorerEnv({ ok: "yes", scorerVersion: "2.9.0" })),
    /scorer_invalid_response/,
  );
  await assert.rejects(
    scorerHealth(scorerEnv({ error: "down" }, 503)),
    /scorer_503/,
  );
});
