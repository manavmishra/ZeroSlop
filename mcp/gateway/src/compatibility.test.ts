import assert from "node:assert/strict";
import test from "node:test";
import { z } from "zod";
import { deslopInputSchema, deslopOutputSchema } from "./contract";
import { writingReportSchema } from "./scorer";

// Freeze the published 2.9.2 validation contract before introducing another transport.
// New input and diagnostics fields are optional; published fields remain unchanged.
test("optional cleanup and diagnostics preserve the published MCP validation contract", () => {
  const legacyInput = z.object({
    text: z.string().trim().min(1).max(20_000)
      .describe("The complete draft supplied as data for editing."),
    genre: z.enum(["general", "social", "email", "research", "professional"])
      .default("general")
      .describe("Publication context: social for LinkedIn or X; research and professional retain formal register."),
    audience: z.string().trim().max(200).optional()
      .describe("Optional intended reader or destination when that context is not clear from the draft."),
  });
  const legacyOutput = z.object({
    text: z.string(),
    status: z.enum([
      "rewritten", "rewritten_with_warnings", "already_clear",
      "unchanged_no_better_version", "unchanged_verification_failed", "unchanged_service_unavailable",
    ]),
    before: writingReportSchema,
    after: writingReportSchema,
    scoreChange: z.number().min(-100).max(100),
    factsPreserved: z.boolean(),
    passedFinalChecks: z.boolean(),
    independentModelChecks: z.number().int().nonnegative(),
    modelRequests: z.number().int().min(0).max(2),
    rolesCompleted: z.number().int().nonnegative(),
    finishingRounds: z.number().int().nonnegative(),
    scorerVersion: z.string(),
    durationMs: z.number().int().nonnegative(),
    note: z.string(),
  });
  const extendedInput = z.toJSONSchema(deslopInputSchema);
  const publishedInput = z.toJSONSchema(legacyInput);
  for (const io of ["input", "output"] as const) {
    const metadata = z.toJSONSchema(deslopInputSchema, { io });
    const { operation: _operation, ...publishedProperties } = metadata.properties!;
    assert.deepEqual({ ...metadata, properties: publishedProperties }, z.toJSONSchema(legacyInput, { io }));
  }
  assert.deepEqual(extendedInput.required, publishedInput.required);
  assert.deepEqual(Object.keys(extendedInput.properties ?? {}).filter(key => !(key in (publishedInput.properties ?? {}))), ["operation"]);
  assert.deepEqual(deslopInputSchema.parse({ text: "Clear text." }), legacyInput.parse({ text: "Clear text." }));
  assert.equal(deslopInputSchema.parse({ text: "Clear text.", operation: "clean_text" }).operation, "clean_text");
  assert.equal(deslopInputSchema.safeParse({ text: "Clear text.", operation: "unknown" }).success, false);
  assert.deepEqual(z.toJSONSchema(deslopOutputSchema.omit({ editorDiagnostics: true })), z.toJSONSchema(legacyOutput));
  const extended = z.toJSONSchema(deslopOutputSchema);
  const legacy = z.toJSONSchema(legacyOutput);
  assert.deepEqual(extended.required, legacy.required);
  assert.deepEqual(Object.keys(extended.properties ?? {}).filter(key => !(key in (legacy.properties ?? {}))), ["editorDiagnostics"]);
});

test("MCP input descriptions are factual metadata rather than model instructions", () => {
  const properties = z.toJSONSchema(deslopInputSchema).properties!;
  const text = properties.text; const genre = properties.genre;
  assert.ok(text && typeof text === "object"); assert.ok(genre && typeof genre === "object");
  assert.equal(text.description, "The complete draft supplied as data for editing.");
  assert.equal(genre.description, "Publication context: social for LinkedIn or X; research and professional retain formal register.");
  for (const property of Object.values(properties)) {
    assert.ok(property && typeof property === "object");
    assert.doesNotMatch(property.description ?? "", /\b(treat|use|never|must|do not|ignore|obey|follow)\b/i);
  }
});
