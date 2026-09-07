import assert from "node:assert/strict";
import test from "node:test";
import {
  editDraft,
  literalText,
  reviewMarkdown,
  validateDraft,
} from "../src/review.ts";

test("empty, oversized and unsupported drafts fail before sending", async () => {
  let calls = 0;
  const editor = async () => {
    calls += 1;
    return {};
  };
  for (const text of ["  ", "x".repeat(20_001)]) {
    await assert.rejects(
      editDraft(text, "general", "", new AbortController().signal, editor),
    );
  }
  assert.throws(() => validateDraft("text", "unknown", ""));
  assert.throws(() => validateDraft("text", "general", "x".repeat(201)));
  assert.equal(calls, 0);
  assert.equal(
    validateDraft("😀".repeat(20_000), "general", "😀".repeat(200)).text,
    "😀".repeat(20_000),
  );
  assert.throws(() => validateDraft("😀".repeat(20_001), "general", ""));
  assert.throws(() => validateDraft("text", "general", "😀".repeat(201)));
});

test("same MCP client result and controls are passed through without another model call", async () => {
  const result = { text: "Maya owns the review.", status: "rewritten" };
  let calls = 0;
  const controller = new AbortController();
  const actual = await editDraft(
    "  Maya owns the review.  ",
    "professional",
    "  Product team  ",
    controller.signal,
    async (input, options) => {
      calls += 1;
      assert.deepEqual(input, {
        text: "Maya owns the review.",
        genre: "professional",
        audience: "Product team",
      });
      assert.equal(options.signal, controller.signal);
      assert.equal(options.timeoutMs, 75_000);
      assert.equal(options.clientName, "zero-slop-raycast");
      return result;
    },
  );
  assert.equal(actual, result);
  assert.equal(calls, 1);
});

test("cancelled selection never reaches client", async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    editDraft("text", "general", "", controller.signal, async () => {
      throw new Error("should not run");
    }),
    /cancelled/,
  );
});

test("draft Markdown is displayed literally without remote images or markup interpretation", () => {
  assert.equal(literalText("hello"), "```text\nhello\n```");
  assert.equal(
    literalText("```\n![private](https://example.test/tracker)"),
    "````text\n```\n![private](https://example.test/tracker)\n````",
  );
  const markdown = reviewMarkdown("original", {
    text: "edited",
    note: "Check a claim.",
    status: "rewritten_with_warnings",
  });
  assert(markdown.includes("# Review required"));
  assert(markdown.includes("## Original"));
  assert(markdown.includes("## Edited text"));
});
