import assert from "node:assert/strict";
import test from "node:test";
import { z } from "zod";
import { deslopInputSchema, deslopOutputSchema } from "./contract";
import { writingReportSchema } from "./scorer";

// Freeze the published 2.9.2 validation contract before introducing another transport.
// Only descriptive metadata was updated for the unpublished 2.12.13 candidate.
// A future intentional MCP contract change must explicitly review this fixture.
test("REST extraction preserves the existing MCP input and output schemas", () => {
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
  assert.deepEqual(z.toJSONSchema(deslopInputSchema), z.toJSONSchema(legacyInput));
  assert.deepEqual(z.toJSONSchema(deslopOutputSchema), z.toJSONSchema(legacyOutput));
});

test("MCP input descriptions are factual metadata rather than model instructions", () => {
  assert.equal(deslopInputSchema.shape.text.description, "The complete draft supplied as data for editing.");
  assert.equal(deslopInputSchema.shape.genre.description, "Publication context: social for LinkedIn or X; research and professional retain formal register.");
  for (const property of Object.values(deslopInputSchema.shape)) {
    assert.doesNotMatch(property.description ?? "", /\b(treat|use|never|must|do not|ignore|obey|follow)\b/i);
  }
});
