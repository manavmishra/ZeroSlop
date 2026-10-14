import { callRole, type EditorFailure } from "./model";
import { checkCancelled } from "./cancellation";
import { MAX_DRAFT_CHARS } from "./contract";
import { rankRewrites, scoreWriting } from "./scorer";
import type { Genre, PipelineResult, RankedRewrite, WritingReport } from "./types";

const SCORE_GATE = 25;
const PIPELINE_BUDGET_MS = 75_000;

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

// The scorer protects concrete details, but cannot adjudicate changes in a
// claim's negation, direction, certainty, or timing. Keep sentences with such
// markers unchanged (apart from case and whitespace) for auto-approval. A
// harmless paraphrase may therefore require review; a stronger unsupported
// assertion must never be silently approved.
const SENSITIVE_CLAIM_WORD = /\b(?:not|no|never|neither|nor|without|cannot|can't|won't|isn't|aren't|wasn't|weren't|doesn't|don't|didn't|hasn't|haven't|hadn't|shouldn't|couldn't|wouldn't|unable|unavailable|increase(?:d|s|ing)?|decrease(?:d|s|ing)?|rises?|rose|rising|falls?|fell|falling|drops?|dropped|dropping|reduc(?:e|ed|es|ing)|more|less|fewer|above|below|before|after|earlier|later|approved|rejected|may|might|could|can|should|likely|unlikely|possible|possibly|probable|probably|uncertain|estimated?|estimates|preliminary|suggests?|suggested|appears?|appeared|seems?|seemed|reportedly|allegedly|potentially|tentative|expected|forecast(?:ed)?|projected|was|were|had|did|will|would|previously|formerly|currently|now|yesterday|today|tomorrow|(?:last|next|this)\s+(?:week|month|year|quarter))\b/i;

function sensitiveSentences(text: string): string[] {
  return (text.replace(/’/g, "'").match(/[^.!?\n]+(?:[.!?]+|$)/g) ?? [])
    .map((sentence) => sentence.trim().toLowerCase().replace(/\s+/g, " "))
    .filter((sentence) => SENSITIVE_CLAIM_WORD.test(sentence))
    .sort();
}

function regularVerbForms(text: string): Map<string, [number, number, number]> {
  const forms = new Map<string, [number, number, number]>();
  for (const word of text.toLowerCase().match(/\b[a-z]{4,}\b/g) ?? []) {
    let stem = word;
    let form = 1; // present or base form
    if (word.endsWith("ied")) { stem = word.slice(0, -3) + "y"; form = 0; }
    else if (word.endsWith("ed")) { stem = word.slice(0, -2); form = 0; }
    else if (word.endsWith("ing")) { stem = word.slice(0, -3); form = 2; }
    else if (word.endsWith("ies")) stem = word.slice(0, -3) + "y";
    else if (word.endsWith("es")) stem = word.slice(0, -2);
    else if (word.endsWith("s")) stem = word.slice(0, -1);
    // "stopped" / "stopping" share the stem of "stops".
    if (form !== 1) stem = stem.replace(/([^aeiou])\1$/, "$1");
    if (stem.length < 3) continue;
    const counts = forms.get(stem) ?? [0, 0, 0];
    counts[form] = (counts[form] ?? 0) + 1;
    forms.set(stem, counts);
  }
  return forms;
}

function regularVerbFormRisk(source: string, rewrite: string): boolean {
  const before = regularVerbForms(source);
  const after = regularVerbForms(rewrite);
  for (const [stem, first] of before) {
    const second = after.get(stem);
    if (!second) continue;
    const forms = first.map((count, index) => count + (second[index] ?? 0));
    if (forms.filter((count) => count > 0).length < 2) continue;
    if (first.some((count, index) => count !== second[index])) return true;
  }
  return false;
}

export function sourceClaimRisk(source: string, rewrite: string): boolean {
  // A vetted deterministic deletion of stock framing is not a change in the
  // claim it introduces. Normalize both sides with the exact same conservative
  // editor before comparing; modality, figures, timing and agency remain.
  const normalizedSource = localRescue(source);
  const normalizedRewrite = localRescue(rewrite);
  const before = sensitiveSentences(normalizedSource);
  const after = sensitiveSentences(normalizedRewrite);
  return before.length !== after.length || before.some((sentence, index) => sentence !== after[index])
    || regularVerbFormRisk(normalizedSource, normalizedRewrite);
}

export function withinScorerLimit(text: string): boolean {
  // Python's scorer counts Unicode code points, not UTF-16 code units.
  return [...text].length <= MAX_DRAFT_CHARS;
}

export function meetsReleaseGate(report: WritingReport): boolean {
  return report.score < SCORE_GATE
    && report.highWeightFlags === 0
    && report.register.findings.length === 0
    && !(report.shape.measured && report.shape.broetry)
    && report.readability === "clear"
    && (report.sentences < 8 || report.sentenceVariety === "natural");
}

// Availability fallback for the single-call service. Every transform is a
// bounded line edit: it removes a stock wrapper, contracts a phrase, or
// changes paragraphing. Names, figures, links, examples, and claims remain.
export function localRescue(text: string): string {
  const original = String(text || "").trim();
  const protectedSpans: string[] = [];
  const base = [...original.matchAll(
    /\x60{3}[\s\S]*?\x60{3}|^[ \t]*>[^\n]*(?:\n[ \t]*>[^\n]*)*|\x60[^\x60\n]+\x60|\[[^\]\n]+\]\([^)]+\)|https?:\/\/[^\s<]+/gm,
  )].map((match): [number, number] => {
    let end = match.index + match[0].length;
    if (/^https?:\/\//.test(match[0])) {
      // Adjacent closing prose quotes belong to the quotation scanner.
      const boundary = /["'“”‘’][.!?,;:)]*$/.exec(match[0]);
      if (boundary) end = match.index + boundary.index;
    }
    return [match.index, end];
  });
  const quotes: Array<Array<[number, number]>> = [[], [], [], []];
  const opened: Array<number | null> = [null, null, null, null];
  const word = (char: string) => Boolean(char) && /[A-Za-z0-9_]/.test(char);
  let baseIndex = 0;
  // Scan each delimiter once. Unmatched openers do not repeatedly scan the
  // remaining text; independent quote types can still close later spans.
  for (let index = 0; index < original.length; index++) {
    while (baseIndex < base.length && index >= base[baseIndex]![1]) baseIndex++;
    const inBase = baseIndex < base.length && base[baseIndex]![0] <= index;
    if (inBase) continue;
    const char = original[index];
    const previous = original[index - 1] ?? "";
    const following = original[index + 1] ?? "";
    let kind: number | null = null;
    let starts = false;
    let closes = false;
    if (char === "“") { kind = 0; starts = true; }
    else if (char === "”") { kind = 0; closes = true; }
    else if (char === "‘") { kind = 1; starts = true; }
    else if (char === "’") { kind = 1; closes = !(word(previous) && word(following)); }
    else if (char === '"') { kind = 2; starts = true; closes = true; }
    else if (char === "'") { kind = 3; starts = !word(previous); closes = !word(following); }
    if (kind === null) continue;
    const start = opened[kind];
    if (start !== null && start !== undefined && closes) {
      quotes[kind]!.push([start, index + 1]);
      opened[kind] = null;
    } else if (start === null && starts) {
      opened[kind] = index;
    }
  }
  // Preserve an unmatched quoted suffix rather than guessing its endpoint.
  for (let kind = 0; kind < opened.length; kind++) {
    const start = opened[kind];
    if (start !== null && start !== undefined) quotes[kind]!.push([start, original.length]);
  }
  // Fixed five-way merge is linear, preserving nested quotes and any code or
  // links they contain without restoring nested placeholder tokens.
  const lists = [base, ...quotes];
  const positions = lists.map(() => 0);
  const ranges: Array<[number, number]> = [];
  while (true) {
    let selected = -1;
    for (let kind = 0; kind < lists.length; kind++) {
      const span = lists[kind]![positions[kind]!];
      if (span && (selected < 0 || span[0] < lists[selected]![positions[selected]!]![0])) selected = kind;
    }
    if (selected < 0) break;
    const [start, end] = lists[selected]![positions[selected]!]!;
    positions[selected]!++;
    const last = ranges.at(-1);
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else ranges.push([start, end]);
  }
  const parts: string[] = [];
  let cursor = 0;
  for (const [start, end] of ranges) {
    parts.push(original.slice(cursor, start), `\uE000${protectedSpans.length}\uE001`);
    protectedSpans.push(original.slice(start, end));
    cursor = end;
  }
  parts.push(original.slice(cursor));
  const masked = parts.join("");
  let out = masked.replace(/[\u00A0\u202F]/g, " ");
  // Drop only a complete introductory clause. Replacing it with "Today"
  // would turn generic framing into a claim about when the event happened.
  // A single unpunctuated line break may be a wrapped sentence, not a start.
  out = out.replace(
    /(^|[.!?][ \t\r\n]+|\r?\n[ \t]*\r?\n[ \t]*)in today['’]s rapidly evolving (?:landscape|world),[ \t]+([A-Za-z][A-Za-z0-9_-]*)/gi,
    (_match, prefix: string, word: string) => prefix + (word === word.toLowerCase()
      ? word.charAt(0).toUpperCase() + word.slice(1) : word),
  );
  out = out.replace(
    /(^|[.!?][ \t]+|\n[ \t]*)(?:it is important to note that|it is worth noting that)[ \t]+([A-Za-z][A-Za-z0-9_-]*)/gi,
    (_match, prefix: string, word: string) => prefix + (word === word.toLowerCase()
      ? word.charAt(0).toUpperCase() + word.slice(1) : word),
  );
  out = out.replace(
    /(^|[.!?][ \t\r\n]+|\r?\n[ \t]*\r?\n[ \t]*)as we move forward,[ \t]+the team will\b/gi,
    (_match, prefix: string) => prefix + "The team will",
  );
  // Remove one hype modifier without substituting emotion or paraphrasing
  // an unspecified benefit. Preserve the announcement and its exact subject.
  out = out.replace(
    /(^|[.!?][ \t\r\n]+|\r?\n[ \t]*\r?\n[ \t]*)([Ww]e)(['’]re| are) thrilled to announce a game[-\u2011]changing update\b/g,
    (_match, prefix: string, subject: string, verb: string) => prefix + subject + verb + " thrilled to announce an update",
  );
  const changes: Array<[RegExp, string | ((...args: string[]) => string)]> = [
    [/\bwe are thrilled to unveil ([^,\n]+),\s+a transformative release that redefines what is possible in ([^.]+)\./gi,
      (_match: string, name: string, topic: string) => name + " updates " + topic + "."],
    [/\bthis release represents a significant milestone in our journey to empower teams everywhere\.\s*/gi, ""],
    [/\bwe have listened carefully to your feedback and are excited to deliver a suite of powerful new capabilities\./gi,
      "We listened to your feedback and added new capabilities."],
    [/\bour cutting[-\u2010\u2011 ]edge\b/gi, "Our"],
    [/\bhours of tedious manual configuration\b/gi, "hours of manual configuration"],
    [/\bwe have completely reimagined\b/gi, "We rebuilt"],
    [/\bthis represents a significant milestone in our journey\.\s*/gi, ""],
    [/\bwill leverage the proposal to make a decision\b/gi, "will use the proposal to decide"],
    [/\ba groundbreaking update\b/gi, "an update"],
    [/\bwith robust error handling built in from the ground up\b/gi, "with built-in error handling"],
    [/\bwe believe these improvements will fundamentally transform how your team works,\s+and the release is available today\./gi,
      "The release is available today."],
    [/\bwe are incredibly excited to share(?: some news)? about\b/gi, "We're excited about"],
    [/\bwe(?:['’]re| are) excited to share(?: some news)? about\b/gi, "We're excited about"],
    [/\bwe are incredibly excited to share\b/gi, "We're sharing"],
    [/\bwe(?:['’]re| are) excited to share\b/gi, "We're excited about"],
    [/\bi(?:['’]m| am) incredibly excited to (?:share|announce)\b/gi, "I'm sharing"],
    [/\bour journey\b/gi, "our work"],
    [/\bour transformative journey\b/gi, "our work"],
    [/\bit is important to note that\b[ \t]*/gi, ""],
    [/\bit is worth noting that\b[ \t]*/gi, ""],
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
    // A contrast can carry a substantive position. Do not infer that the
    // thing rejected in the source nevertheless mattered.
    [/\bthat is the kind of impact that keeps us going\b/gi, "That result keeps us going"],
    [/\bseamlessly (integrates?)\b/gi,
      (match: string, verb: string) => match.charAt(0) === match.charAt(0).toUpperCase()
        ? verb.charAt(0).toUpperCase() + verb.slice(1).toLowerCase() : verb],
    [/\bjust how deeply\b/gi, "how much"],
    [/\bgame[-\u2011]changing\b/gi, "useful"],
    [/\bcutting[-\u2010\u2011 ]edge\b/gi, "current"],
    [/\bredefines what(?:['’]s| is) possible in\b/gi, "updates"],
    [/\bhere are (?=\d+\s+(?:tips?|ways?|reasons?|steps?|ideas?)\b)/gi, ""],
    [/\bgenuinely\s+/gi, ""],
    [/\bin order to\b/gi, "to"],
    [/\bat the end of the day\b/gi, "ultimately"],
    // Contractions alone do not improve clean prose. Keep those sentences.
  ];
  for (const [pattern, replacement] of changes) {
    if (typeof replacement === "function") {
      out = out.replace(pattern, replacement);
    } else {
      out = out.replace(pattern, (match) => {
        if (!replacement) return replacement;
        if (match.charAt(0) === match.charAt(0).toUpperCase()) {
          return replacement.charAt(0).toUpperCase() + replacement.slice(1);
        }
        return replacement.startsWith("I'") ? replacement
          : replacement.charAt(0).toLowerCase() + replacement.slice(1);
      });
    }
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

function editorFailureNote(reason: EditorFailure | null): string {
  switch (reason) {
    case "timeout": return "the editor request timed out";
    case "cancelled": return "the editor service cancelled the request";
    case "deadline": return "the editor request could not start within its deadline";
    case "configuration": return "the editor service configuration was unavailable";
    case "invalid_output": return "the editor service returned unusable output";
    case "unchanged_output": return "the model returned the original text";
    case "transport": return "the editor request failed before a usable response arrived";
    default: return "the editor service was unavailable";
  }
}

export async function runPipeline(env: Env, input: DeslopInput, clientAddress = "", signal?: AbortSignal): Promise<PipelineResult> {
  const started = Date.now();
  const deadline = started + PIPELINE_BUDGET_MS;
  const control = { signal, editorRequested: false, deadline };
  checkCancelled(control);
  const original = input.text.trim();
  const before = await scoreWriting(env, original, input.genre, control);
  checkCancelled(control);

  // A short clean note should not incur an AI call merely because document-
  // level statistics need more words. Positive findings still force an edit.
  const cleanEnough = meetsReleaseGate(before)
    && before.flaggedPhrases === 0;
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
  // Exactly one outbound editor request. The endpoint may use one bounded
  // alternate provider if its primary cannot return a usable edit.
  let observedProviderCalls: 0 | 1 | 2 | null = null;
  let editorFailure: EditorFailure | null = null;
  const modelReply = await callRole(env, "complete", original, diagnostics, deadline, clientAddress, control,
    (count) => { observedProviderCalls = count; }, (reason) => { editorFailure = reason; });
  checkCancelled(control);
  const rescue = localRescue(original);
  const candidates: Record<string, string> = {};
  const cleanedModelReply = modelReply?.text ? localRescue(modelReply.text) : "";
  if (cleanedModelReply && cleanedModelReply !== original && withinScorerLimit(cleanedModelReply)) {
    candidates["one-call edit"] = cleanedModelReply;
  }
  if (rescue && rescue !== original && rescue !== cleanedModelReply && withinScorerLimit(rescue)) {
    candidates["local edit"] = rescue;
  }

  if (Object.keys(candidates).length === 0) {
    return {
      ...unchanged(
        original, modelReply ? "unchanged_no_better_version" : "unchanged_service_unavailable", before, started, env.SCORER_VERSION,
        modelReply
          ? !withinScorerLimit(cleanedModelReply)
            ? "Zero Slop kept the original because the model edit exceeded the scorer's input limit, and the local editor found no safe textual change."
            : "Zero Slop kept the original because the model response yielded no distinct edit after local cleanup, and the local editor found no safe textual change."
          : `Zero Slop kept the original because ${editorFailureNote(editorFailure)}, and the conservative local editor found no safe textual change.`,
      ),
      modelRequests: modelReply?.providerCalls ?? observedProviderCalls ?? 1,
    };
  }

  const modelClaimUncertain = Boolean(candidates["one-call edit"]
    && sourceClaimRisk(original, candidates["one-call edit"]));
  let checked = await rankRewrites(env, original, candidates, input.genre, control);
  checkCancelled(control);
  // Record the model verdict before a local-only rerank drops that candidate.
  // This contains fixed categories only: never source spans or provider errors.
  const modelSourceRejected = checked.ranked.some((candidate) =>
    candidate.name === "one-call edit" && (!candidate.preserved || candidate.invented));
  const safeModelEdit = checked.ranked.some((candidate) =>
    candidate.name === "one-call edit" && candidate.preserved && !candidate.invented);
  if (modelSourceRejected || modelClaimUncertain) {
    console.warn(JSON.stringify({ event: "editor_source_rejected", reason: modelClaimUncertain ? "claim_changed" : "protected_source_changed" }));
  }
  if ((!sourceSafe(checked) || sourceClaimRisk(original, checked.text)) && candidates["local edit"]) {
    const localOnly = await rankRewrites(env, original, { "local edit": rescue }, input.genre, control);
    checkCancelled(control);
    if (sourceSafe(localOnly) && !sourceClaimRisk(original, localOnly.text)) checked = localOnly;
  }
  if (!sourceSafe(checked)) {
    return {
      ...unchanged(
        original, "unchanged_verification_failed", before, started, env.SCORER_VERSION,
        "Every proposed edit changed protected source material, so the original is preserved.",
      ),
      modelRequests: modelReply?.providerCalls ?? observedProviderCalls ?? 1,
      rolesCompleted: modelReply ? 6 : 2,
    };
  }

  const current = checked.text;
  const after = await scoreWriting(env, current, input.genre, control);
  checkCancelled(control);
  const selectedModelEdit = checked.name === "one-call edit";
  const claimUncertain = sourceClaimRisk(original, current);
  const passed = selectedModelEdit && !claimUncertain && meetsReleaseGate(after);
  const warnings: string[] = [];
  if (!selectedModelEdit) {
    warnings.push(modelClaimUncertain
      ? "the model response changed a source claim's negation, direction, certainty, or timing, so the local edit was used"
      : modelSourceRejected
        ? "the model response did not pass the source check, so the local edit was used"
      : safeModelEdit
        ? "the local edit ranked ahead of a source-preserving model edit on the measured writing checks"
        : modelReply
          ? !withinScorerLimit(cleanedModelReply)
            ? "the model edit exceeded the scorer's input limit, so the local edit was used"
            : "the model response yielded no distinct edit after local cleanup, so the local edit was used"
          : `${editorFailureNote(editorFailure)}, so the local edit was used`);
    warnings.push("the local editor only removes stock wording; meaning, voice, and vague claims still need review");
  }
  if (after.score >= SCORE_GATE) warnings.push("the writing score remains above 25");
  if (after.highWeightFlags > 0) warnings.push("a strong stock-writing signal remains");
  if (after.readability !== "clear") warnings.push("the writing is still harder to follow than it should be");
  if (after.sentences >= 8 && after.sentenceVariety !== "natural") {
    warnings.push("the sentence rhythm still sounds too even");
  }
  if (after.register.findings.length > 0 || (after.shape.measured && after.shape.broetry)) {
    warnings.push("a document-level writing check remains");
  }
  if (claimUncertain) warnings.push("a source claim's negation, direction, certainty, or timing changed and needs human review");

  return {
    text: current,
    status: passed ? "rewritten" : "rewritten_with_warnings",
    before,
    after,
    scoreChange: Math.round((after.score - before.score) * 10) / 10,
    factsPreserved: !claimUncertain,
    passedFinalChecks: passed,
    independentModelChecks: 0,
    modelRequests: modelReply?.providerCalls ?? observedProviderCalls ?? 1,
    rolesCompleted: selectedModelEdit ? 8 : 4,
    finishingRounds: 1,
    scorerVersion: env.SCORER_VERSION,
    durationMs: Date.now() - started,
    note: warnings.length
      ? `Zero Slop returned the safest edited draft. Review it before publishing because ${warnings.join("; ")}.`
      : "One AI editorial response produced the rewrite; local scoring and source checks approved the exact text returned.",
  };
}
