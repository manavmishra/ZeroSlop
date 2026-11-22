import type { ContextualReview } from "./types";

const KINDS = new Set(["style", "redundancy", "unsupported_claim", "missing_substance"]);

function object(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function bounded(value: unknown, maximum: number): value is string {
  return typeof value === "string" && value.trim().length > 0 && Array.from(value).length <= maximum;
}

/** Validate source anchoring and the response contract, never editorial truth. */
export function contextualReview(value: unknown, source: string, rewrite: string): ContextualReview | null {
  if (!object(value) || Object.keys(value).some((key) => !["decision", "findings"].includes(key))) return null;
  if (typeof value.decision !== "string" || !["edit", "keep", "gap"].includes(value.decision) || !Array.isArray(value.findings)
    || value.findings.length > 8) return null;
  const findings: ContextualReview["findings"] = [];
  for (const finding of value.findings) {
    if (!object(finding) || Object.keys(finding).some((key) => !["kind", "quote", "reason", "question"].includes(key))) return null;
    if (typeof finding.kind !== "string" || !KINDS.has(finding.kind) || !bounded(finding.quote, 400)
      || !source.includes(finding.quote) || !bounded(finding.reason, 500)
      || (finding.question !== undefined && !bounded(finding.question, 300))) return null;
    findings.push({
      kind: finding.kind as ContextualReview["findings"][number]["kind"],
      quote: finding.quote,
      reason: finding.reason,
      ...(finding.question !== undefined ? { question: finding.question as string } : {}),
    });
  }
  const decision = value.decision as ContextualReview["decision"];
  if (decision === "keep" && (rewrite !== source || findings.length !== 0)) return null;
  if (decision === "edit" && (rewrite === source || findings.length === 0)) return null;
  if (decision === "gap" && (rewrite !== source || !findings.some((finding) =>
    ["missing_substance", "unsupported_claim"].includes(finding.kind) && finding.question))) return null;
  return { decision, findings };
}
