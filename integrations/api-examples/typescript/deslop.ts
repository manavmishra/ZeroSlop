// Run with Node.js 22.18+ native TypeScript support. No package installation.
import { readFileSync } from "node:fs";

interface WritingReport { score: number; [field: string]: unknown }
interface DeslopResult {
  text: string;
  status: string; // Unknown future statuses require review.
  before: WritingReport;
  after: WritingReport;
  scoreChange: number;
  factsPreserved: boolean;
  passedFinalChecks: boolean;
  independentModelChecks: number;
  modelRequests: number;
  rolesCompleted: number;
  finishingRounds: number;
  scorerVersion: string;
  durationMs: number;
  note: string;
  [field: string]: unknown;
}

const fields = ["text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
  "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note"];

function approved(value: unknown): boolean {
  if (!value || typeof value !== "object" || fields.some((field) => !Object.hasOwn(value, field))) return false;
  // These checks cover the fields used by the approval decision, not the full OpenAPI schema.
  const result = value as DeslopResult;
  const score = (number: unknown): boolean => typeof number === "number" && Number.isFinite(number) && number >= 0 && number <= 100;
  if (typeof result.text !== "string" || !score(result.before?.score) || !score(result.after?.score) ||
      typeof result.passedFinalChecks !== "boolean") return false;
  return result.factsPreserved === true && (
    (result.status === "rewritten" && result.passedFinalChecks === true) ||
    (result.status === "already_clear" && result.modelRequests === 0 && result.scoreChange === 0 &&
     result.before.score === result.after.score)
  );
}

try {
  const request: unknown = JSON.parse(readFileSync(0, "utf8"));
  const response = await fetch(process.env.ZERO_SLOP_API_URL ?? "https://mcp.zero-slop.ai/v1/deslop", {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(request), redirect: "manual", signal: AbortSignal.timeout(75_000),
  });
  const result: unknown = await response.json();
  if (response.status !== 200) {
    console.error(JSON.stringify({ httpStatus: response.status, retryAfter: response.headers.get("retry-after"), problem: result }));
    process.exitCode = 1;
  } else {
    console.log(JSON.stringify(result));
    if (!approved(result)) {
      console.error("Review required. Keep the original until the result has been reviewed.");
      process.exitCode = 3;
    }
  }
} catch {
  console.error("Request failed or response was not JSON. No automatic retry; the outcome may be unknown.");
  process.exitCode = 1;
}
