import { z } from "zod";

const providerSchema = z.enum(["workers-ai", "openrouter"]);
const failureOutcomeSchema = z.enum(["timeout", "cancelled", "capacity", "invalid_output", "configuration", "unavailable"]);
const httpStatusSchema = z.number().int().min(100).max(599);
// Keep the relationships expressible in the JSON Schema shared by MCP/OpenAPI.
const providerAttemptSchema = z.union([
  z.object({ provider: providerSchema, outcome: z.literal("success"),
    failureStage: z.never().optional(), httpStatus: z.never().optional() }).strict(),
  z.object({ provider: providerSchema, outcome: failureOutcomeSchema,
    failureStage: z.enum(["invoke", "fetch"]).optional(), httpStatus: z.never().optional() }).strict(),
  z.object({ provider: providerSchema, outcome: failureOutcomeSchema,
    failureStage: z.enum(["http", "body"]), httpStatus: httpStatusSchema.optional() }).strict(),
]);

export const editorDiagnosticsSchema = z.object({
  endpointHttpStatus: httpStatusSchema.optional(),
  providerAttempts: z.array(providerAttemptSchema).max(2).optional(),
}).strict();

export type SafeProviderAttempt = z.infer<typeof providerAttemptSchema>;
export type EditorDiagnostics = z.infer<typeof editorDiagnosticsSchema>;

// Endpoint diagnostics are untrusted. Copy only bounded enums and a reported
// numeric status, never messages, drafts, model names or other properties.
export function safeProviderAttempts(value: unknown): SafeProviderAttempt[] {
  if (!value || typeof value !== "object" || !("providerAttempts" in value)) return [];
  const attempts = value.providerAttempts;
  if (!Array.isArray(attempts) || attempts.length > 2) return [];
  const outcomes = ["success", "timeout", "cancelled", "capacity", "invalid_output", "configuration", "unavailable"];
  const safe: SafeProviderAttempt[] = [];
  for (const attempt of attempts) {
    if (!attempt || typeof attempt !== "object" ||
        !["workers-ai", "openrouter"].includes(attempt.provider) || !outcomes.includes(attempt.outcome)) return [];
    const entry: SafeProviderAttempt = { provider: attempt.provider, outcome: attempt.outcome };
    if (attempt.outcome !== "success" && ["invoke", "fetch", "http", "body"].includes(attempt.failureStage)) {
      entry.failureStage = attempt.failureStage;
      if (["http", "body"].includes(attempt.failureStage) && typeof attempt.httpStatus === "number"
          && Number.isSafeInteger(attempt.httpStatus) && attempt.httpStatus >= 100 && attempt.httpStatus <= 599) {
        entry.httpStatus = attempt.httpStatus;
      }
    }
    safe.push(entry);
  }
  return safe;
}

export function safeEditorDiagnostics(status: unknown, payload?: unknown): EditorDiagnostics | undefined {
  const diagnostics: EditorDiagnostics = {};
  if (typeof status === "number" && Number.isSafeInteger(status) && status >= 100 && status <= 599) {
    diagnostics.endpointHttpStatus = status;
  }
  const attempts = safeProviderAttempts(payload);
  if (attempts.length) diagnostics.providerAttempts = attempts;
  return Object.keys(diagnostics).length ? diagnostics : undefined;
}
