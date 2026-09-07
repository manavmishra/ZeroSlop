// Run with Node.js 22+. Read one request object from stdin.
import { readFileSync } from "node:fs";

const endpoint = process.env.ZERO_SLOP_API_URL ?? "https://mcp.zero-slop.ai/v1/deslop";
const fields = ["text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
  "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note"];

export function approved(result) {
  const score = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100;
  if (!result || fields.some((field) => !Object.hasOwn(result, field)) ||
      typeof result.text !== "string" || !score(result.before?.score) || !score(result.after?.score) ||
      typeof result.passedFinalChecks !== "boolean") return false;
  return result.factsPreserved === true && (
    (result.status === "rewritten" && result.passedFinalChecks === true) ||
    (result.status === "already_clear" && result.modelRequests === 0 && result.scoreChange === 0 &&
     result.before.score === result.after.score)
  );
}

try {
  const request = JSON.parse(readFileSync(0, "utf8"));
  const response = await fetch(endpoint, {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(request), redirect: "manual", signal: AbortSignal.timeout(75_000),
  });
  const result = await response.json();
  if (response.status !== 200) {
    // Preserve the complete problem object, including code and requestId.
    console.error(JSON.stringify({ httpStatus: response.status, retryAfter: response.headers.get("retry-after"), problem: result }));
    process.exitCode = 1;
  } else {
    console.log(JSON.stringify(result)); // Preserve every result field, including future additions.
    if (!approved(result)) {
      console.error("Review required. Keep the original until the result has been reviewed.");
      process.exitCode = 3;
    }
  }
} catch {
  console.error("Request failed or response was not JSON. No automatic retry; the outcome may be unknown.");
  process.exitCode = 1;
}
