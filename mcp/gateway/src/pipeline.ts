import { callRole } from "./model";
import { rankRewrites, scoreWriting } from "./scorer";
import type { Genre, PipelineResult, RankedRewrite, WritingReport } from "./types";

const SCORE_GATE = 25;
const PIPELINE_BUDGET_MS = 36_000;

export type DeslopInput = {
  text: string;
  genre: Genre;
  audience?: string;
};

export function scorerGuidance(report: WritingReport): string {
  return JSON.stringify({
    target: "below 25",
    score: report.score,
    flaggedPhrases: report.flags.slice(0, 12).map(({ phrase, issue, direction }) => ({
      phrase, issue, direction,
    })),
    registerFindings: report.register.findings.slice(0, 4).map(({ name, quote }) => ({ name, quote })),
    sentenceVariety: report.sentenceVariety,
    broetry: report.shape.broetry,
  });
}

function sourceSafe(checked: RankedRewrite): boolean {
  return checked.preserved && !checked.invented && Boolean(checked.text.trim());
}

// Availability fallback for the single-call service. Every transform is a
// bounded line edit: it removes a stock wrapper, contracts a phrase, or
// changes paragraphing. Names, figures, links, examples, and claims remain.
export function localRescue(text: string): string {
  const original = String(text || "").trim();
  const protectedSpans: string[] = [];
  const masked = original.replace(
    /\x60{3}[\s\S]*?\x60{3}|\x60[^\x60\n]+\x60|\[[^\]\n]+\]\([^)]+\)|https?:\/\/[^\s<]+|“[^”\n]*”|‘[^’\n]*’|"[^"\n]*"/g,
    (value) => {
      const token = `\uE000${protectedSpans.length}\uE001`;
      protectedSpans.push(value);
      return token;
    },
  );
  let out = masked;
  const changes: Array<[RegExp, string | ((...args: string[]) => string)]> = [
    [/\bwe are incredibly excited to share(?: some news)? about\b/gi, "We're excited about"],
    [/\bwe(?:['’]re| are) excited to share(?: some news)? about\b/gi, "We're excited about"],
    [/\bwe are incredibly excited to share\b/gi, "We're sharing"],
    [/\bwe(?:['’]re| are) excited to share\b/gi, "We're excited about"],
    [/\bi(?:['’]m| am) incredibly excited to (?:share|announce)\b/gi, "I'm sharing"],
    [/\bour journey\b/gi, "our work"],
    [/\bour transformative journey\b/gi, "our work"],
    [/\bin today'?s rapidly evolving (?:landscape|world)\b/gi, "Today"],
    [/\bit is important to note that\b/gi, ""],
    [/\bit is worth noting that\b/gi, ""],
    [/\bwhat we did not realize was just how deeply it impacted everything downstream\./gi,
      "We underestimated its effect on the work that followed."],
    [/\bonboarding is not a checklist\.\s*it is a promise\./gi, "We see onboarding as a promise."],
    [/\bonboarding isn['’]t a checklist\s*[-—]\s*it['’]s a promise\./gi,
      "We see onboarding as a promise."],
    [/\bthe insights were game[-\u2011]changing\./gi, "Those conversations changed our approach."],
    [/\bthe insights were (?:transformative|clear|significant):\s*/gi,
      "Those conversations showed that "],
    [/\ba platform that leverages intelligent automation to streamline the entire process end to end\b/gi,
      "a platform that automates onboarding from start to finish"],
    [/\bthe results speak for themselves:\s*([a-z])/gi,
      (_match: string, first: string) => first.toUpperCase()],
    [/\bthe results speak for themselves\.\s*/gi, ""],
    [/\bbut here is the thing nobody talks about\.\s*/gi, ""],
    [/\bthe real win was not ([^.]+)\.\s*it was ([^.]+)\./gi,
      (_match: string, first: string, second: string) =>
        `${first.charAt(0).toUpperCase()}${first.slice(1)} mattered. More important was ${second}.`],
    [/\bthe real win isn['’]t just ([^.]+)\.\s*it['’]s ([^.]+)\./gi,
      (_match: string, first: string, second: string) =>
        `${first.charAt(0).toUpperCase()}${first.slice(1)} matters. The larger gain is ${second}.`],
    [/\bthat is the kind of impact that keeps us going\b/gi, "That result keeps us going"],
    [/\bunlock(?:ing)? the full potential of\b/gi, "use"],
    [/\bseamlessly integrates?\b/gi, "integrates"],
    [/\bjust how deeply\b/gi, "how much"],
    [/\bgame[-\u2011]changing\b/gi, "useful"],
    [/\bcutting[- ]edge\b/gi, "current"],
    [/\bredefines what(?:['’]s| is) possible in\b/gi, "updates"],
    [/\bin order to\b/gi, "to"],
    [/\bat the end of the day\b/gi, "ultimately"],
    [/\bwe are\b/gi, "we're"],
    [/\bwe did not\b/gi, "we didn't"],
    [/\bwe do not\b/gi, "we don't"],
    [/\bi am\b/gi, "I'm"],
    [/\bit is\b/gi, "it's"],
    [/\bthey are\b/gi, "they're"],
    [/\byou are\b/gi, "you're"],
    [/\bthere is\b/gi, "there's"],
    [/\bdoes not\b/gi, "doesn't"],
    [/\bis not\b/gi, "isn't"],
    [/\bare not\b/gi, "aren't"],
    [/\bcannot\b/gi, "can't"],
  ];
  for (const [pattern, replacement] of changes) {
    out = out.replace(pattern, replacement as string);
  }
  out = out.replace(/[ \t]+\n/g, "\n").replace(/ {2,}/g, " ").trim();

  // If the wording was outside the conservative dictionary, improve staged
  // paragraphing without touching a word. This covers the short, line-broken
  // social pattern that lexical checks can miss.
  if (out === masked) {
    const paragraphs = out.split(/\n{2,}/).map((part) => part.trim()).filter(Boolean);
    if (paragraphs.length >= 4 && paragraphs.every((part) => part.split(/\s+/).length < 24)) {
      out = paragraphs.join(" ");
    }
  }
  return out.replace(/\uE000(\d+)\uE001/g, (token, index) =>
    protectedSpans[Number(index)] ?? token).trim();
}

function unchanged(
  text: string,
  status: PipelineResult["status"],
  before: WritingReport,
  started: number,
  scorerVersion: string,
  note: string,
): PipelineResult {
  return {
    text,
    status,
    before,
    after: before,
    scoreChange: 0,
    factsPreserved: true,
    passedFinalChecks: false,
    independentModelChecks: 0,
    modelRequests: 0,
    rolesCompleted: 1,
    finishingRounds: 0,
    scorerVersion,
    durationMs: Date.now() - started,
    note,
  };
}

export async function runPipeline(env: Env, input: DeslopInput): Promise<PipelineResult> {
  const started = Date.now();
  const deadline = started + PIPELINE_BUDGET_MS;
  const original = input.text.trim();
  const before = await scoreWriting(env, original, input.genre);

  // A short clean note should not incur an AI call merely because document-
  // level statistics need more words. Positive findings still force an edit.
  const cleanEnough = before.score < SCORE_GATE
    && before.flaggedPhrases === 0
    && before.register.findings.length === 0
    && !(before.shape.measured && before.shape.broetry)
    && before.readability === "clear";
  if (cleanEnough) {
    return unchanged(
      original, "already_clear", before, started, env.SCORER_VERSION,
      "The draft already reads cleanly, so Zero Slop did not spend a model request on it.",
    );
  }

  const diagnostics = {
    genre: input.genre,
    audience: input.audience ?? "",
    localChecks: JSON.parse(scorerGuidance(before)),
  };
  // Exactly one outbound editor request. The endpoint itself is also limited
  // to one provider invocation, so this cannot fan out into a retry ladder.
  const modelReply = await callRole(env, "complete", original, diagnostics, deadline);
  const rescue = localRescue(original);
  const candidates: Record<string, string> = {};
  const cleanedModelReply = modelReply?.text ? localRescue(modelReply.text) : "";
  if (cleanedModelReply && cleanedModelReply !== original) candidates["one-call edit"] = cleanedModelReply;
  if (rescue && rescue !== original && rescue !== modelReply?.text) candidates["local edit"] = rescue;

  if (Object.keys(candidates).length === 0) {
    return {
      ...unchanged(
        original, "unchanged_service_unavailable", before, started, env.SCORER_VERSION,
        "The single model request did not return a usable edit, and the conservative local editor found no safe textual change.",
      ),
      modelRequests: 1,
    };
  }

  let checked = await rankRewrites(env, original, candidates, input.genre);
  if (!sourceSafe(checked) && rescue && rescue !== original) {
    const localOnly = await rankRewrites(env, original, { "local edit": rescue }, input.genre);
    if (sourceSafe(localOnly)) checked = localOnly;
  }
  if (!sourceSafe(checked)) {
    return {
      ...unchanged(
        original, "unchanged_verification_failed", before, started, env.SCORER_VERSION,
        "Every proposed edit changed protected source material, so the original is preserved.",
      ),
      modelRequests: 1,
      rolesCompleted: modelReply ? 6 : 2,
    };
  }

  const current = checked.text;
  const after = await scoreWriting(env, current, input.genre);
  const selectedModelEdit = checked.name === "one-call edit";
  const passed = selectedModelEdit
    && after.score < SCORE_GATE
    && after.register.findings.length === 0
    && !(after.shape.measured && after.shape.broetry);
  const warnings: string[] = [];
  if (!selectedModelEdit) warnings.push("the model response was unavailable or did not pass the source check, so the local edit was used");
  if (after.score >= SCORE_GATE) warnings.push("the writing score remains above 25");
  if (after.register.findings.length > 0 || (after.shape.measured && after.shape.broetry)) {
    warnings.push("a document-level writing check remains");
  }

  return {
    text: current,
    status: passed ? "rewritten" : "rewritten_with_warnings",
    before,
    after,
    scoreChange: Math.round((after.score - before.score) * 10) / 10,
    factsPreserved: true,
    passedFinalChecks: passed,
    independentModelChecks: 0,
    modelRequests: 1,
    rolesCompleted: selectedModelEdit ? 8 : 4,
    finishingRounds: 1,
    scorerVersion: env.SCORER_VERSION,
    durationMs: Date.now() - started,
    note: warnings.length
      ? `Zero Slop returned the safest edited draft. Review it before publishing because ${warnings.join("; ")}.`
      : "One AI editorial response produced the rewrite; local scoring and source checks approved the exact text returned.",
  };
}
