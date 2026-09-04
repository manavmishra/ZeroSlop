import assert from "node:assert/strict";
import test from "node:test";

import { readBoundedJson } from "./bounded-json";

test("reads bounded UTF-8 JSON responses", async () => {
  const payload = await readBoundedJson(Response.json({ text: "Résumé 🧭" }), 1_024);
  assert.deepEqual(payload, { text: "Résumé 🧭" });
});

test("rejects declared and streamed responses above the byte limit", async () => {
  await assert.rejects(
    readBoundedJson(new Response("{}", { headers: { "content-length": "999" } }), 10),
    /response_too_large/,
  );
  await assert.rejects(
    readBoundedJson(new Response(JSON.stringify({ text: "x".repeat(100) })), 20),
    /response_too_large/,
  );
});

test("rejects empty, malformed, and invalid-length responses", async () => {
  await assert.rejects(readBoundedJson(new Response(null), 20), /response_empty/);
  await assert.rejects(readBoundedJson(new Response("not-json"), 20), /response_invalid_json/);
  await assert.rejects(
    readBoundedJson(new Response("{}", { headers: { "content-length": "NaN" } }), 20),
    /response_invalid_length/,
  );
});
