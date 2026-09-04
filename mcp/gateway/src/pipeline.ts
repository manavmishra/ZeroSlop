import { callRole } from "./model";
import { inventoryChanges, rankRewrites, scoreWriting } from "./scorer";
import type { Genre, PipelineResult, RankedRewrite, WritingReport } from "./types";

const SCORE_GATE = 25;
const MAX_REWRITE_ROUNDS = 3;
const MAX_FINAL_ROUNDS = 3;
const PIPELINE_BUDGET_MS = 52_000;

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
      phrase,
      issue,
      direction,
    })),
    registerFindings: report.register.findings.slice(0, 4).map(({ name, quote }) => ({
      name,
      quote,
    })),
    sentenceVariety: report.sentenceVariety,
    broetry: report.shape.broetry,
  });
}

export function verifierPassed(verdict: string | null): boolean {
  return typeof verdict === "string" && /^ok[.!]?$/i.test(verdict.trim());
}

export function releaseReady(
  checked: RankedRewrite,
  report: WritingReport,
  verdicts: Array<string | null>,
  verifierRungs: string[],
): boolean {
  return checked.preserved
    && !checked.invented
    && checked.after < SCORE_GATE
    && report.register.findings.length === 0
    && !report.shape.broetry
    && verdicts.length === 2
    && verdicts.every(verifierPassed)
    && verifierRungs.length === 2
    && new Set(verifierRungs).size === 2;
}

function independentApprovals(
  verdicts: Array<string | null>,
  verifierRungs: string[],
): number {
  if (verifierRungs.length !== 2 || new Set(verifierRungs).size !== 2) return 0;
  return verdicts.filter(verifierPassed).length;
}

function unchanged(
  text: string,
  status: PipelineResult["status"],
  before: WritingReport,
  started: number,
  scorerVersion: string,
  rolesCompleted: number,
  finishingRounds: number,
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
    rolesCompleted,
    finishingRounds,
    scorerVersion,
    durationMs: Date.now() - started,
    note,
  };
}

async function acceptNonWorsening(
  env: Env,
  original: string,
  name: string,
  proposed: string | null,
  current: string,
  checked: RankedRewrite,
  genre: Genre,
): Promise<{ text: string; checked: RankedRewrite; available: boolean }> {
  if (!proposed) return { text: current, checked, available: false };
  const next = await rankRewrites(env, original, { [name]: proposed }, genre);
  if (next.preserved && !next.invented && next.after <= checked.after) {
    return { text: proposed, checked: next, available: true };
  }
  return { text: current, checked, available: true };
}

async function callRoleWithRecovery(
  env: Env,
  role: Parameters<typeof callRole>[1],
  packet: string,
  expectedText: string,
  deadline: number,
  exclude: string[] = [],
  strictExclude = false,
) {
  const first = await callRole(
    env, role, packet, expectedText, deadline, exclude, strictExclude,
  );
  if (first) return first;
  return callRole(
    env, role, packet, expectedText, deadline, exclude, strictExclude,
  );
}

export async function runPipeline(env: Env, input: DeslopInput): Promise<PipelineResult> {
  const started = Date.now();
  const deadline = started + PIPELINE_BUDGET_MS;
  const original = input.text.trim();
  let rolesCompleted = 0;
  const before = await scoreWriting(env, original, input.genre);
  rolesCompleted += 1;

  if (before.score < SCORE_GATE
      && before.register.measured
      && before.register.findings.length === 0
      && !(before.shape.measured && before.shape.broetry)) {
    return unchanged(
      original,
      "already_clear",
      before,
      started,
      env.SCORER_VERSION,
      rolesCompleted,
      0,
      "The original already clears the Zero Slop score and document checks, so it was not sent to an editing model.",
    );
  }

  const context = input.audience
    ? `CALLER CONTEXT:\nAudience or destination: ${input.audience}\n\n`
    : "";
  const notesReply = await callRole(env, "interpret", context + original, original, deadline);
  const notes = notesReply?.text ?? null;
  rolesCompleted += 1;

  let rewriteSource = original;
  let brief = [
    context.trim(),
    notes ? `EDITOR NOTES:\n${notes}` : "",
    `LOCAL SCORER:\n${scorerGuidance(before)}`,
    "Remove the scorer's listed surface patterns while preserving the underlying claims.",
    `DRAFT:\n${original}`,
  ].filter(Boolean).join("\n\n");
  const candidates: Record<string, string> = { "your draft": original };
  const spentRungs: string[] = [];
  let rewriteTrial: RankedRewrite | null = null;
  for (let rewriteRound = 0; rewriteRound < MAX_REWRITE_ROUNDS; rewriteRound += 1) {
    const strategies = rewriteRound === 0
      ? (["rewrite_strip", "rewrite_warm"] as const)
      : (["rewrite_surgical"] as const);
    for (const strategy of strategies) {
      const written = await callRole(
        env,
        strategy,
        brief,
        rewriteSource,
        deadline,
        spentRungs,
        // Prefer a fresh rung, but do not turn a healthy one-model fallback
        // into an outage. The retry changes both the role and scorer guidance;
        // strict model independence remains mandatory for verification below.
        false,
      );
      if (!written) continue;
      if (!spentRungs.includes(written.rung)) spentRungs.push(written.rung);
      const label = strategy === "rewrite_strip"
        ? "cut hard"
        : strategy === "rewrite_warm" ? "keep the warmth" : "surgical retry";
      candidates[`${label}${rewriteRound ? ` (retry ${rewriteRound})` : ""}`] = written.text;
    }
    if (Object.keys(candidates).length === 1) continue;
    rewriteTrial = await rankRewrites(env, original, candidates, input.genre);
    if (rewriteTrial.name !== "your draft" && rewriteTrial.after < SCORE_GATE) break;
    if (rewriteRound < MAX_REWRITE_ROUNDS - 1 && rewriteTrial.name !== "your draft") {
      rewriteSource = rewriteTrial.text;
      const retryReport = await scoreWriting(env, rewriteSource, input.genre);
      brief = [
        context.trim(),
        notes ? `SOURCE NOTES:\n${notes}` : "",
        `LOCAL SCORER ON THE PREVIOUS ATTEMPT:\n${scorerGuidance(retryReport)}`,
        "Rewrite the previous attempt again. Remove every listed surface pattern. Preserve the source facts in the notes; the deterministic fact gate will compare the result with the original.",
        `DRAFT:\n${rewriteSource}`,
      ].filter(Boolean).join("\n\n");
    }
    console.log(JSON.stringify({
      event: "pipeline_rewrite_retry",
      round: rewriteRound + 1,
      score: rewriteTrial.after,
      selectedSource: rewriteTrial.name === "your draft",
      rungsTried: spentRungs.length,
    }));
  }
  rolesCompleted += 1;
  if (Object.keys(candidates).length === 1) {
    return unchanged(
      original,
      "unchanged_service_unavailable",
      before,
      started,
      env.SCORER_VERSION,
      rolesCompleted,
      0,
      "The editing models were unavailable, so the original comes back unchanged.",
    );
  }

  let checked = rewriteTrial ?? await rankRewrites(env, original, candidates, input.genre);
  if (checked.text === original) {
    const editedCandidates = Object.fromEntries(
      Object.entries(candidates).filter(([, text]) => text !== original),
    );
    if (Object.keys(editedCandidates).length > 0) {
      const edited = await rankRewrites(env, original, editedCandidates, input.genre);
      if (edited.preserved && !edited.invented) checked = edited;
    }
  }
  let current = checked.text;
  rolesCompleted += 1;
  console.log(JSON.stringify({
    event: "pipeline_ranked",
    selectedSource: checked.name === "your draft",
    score: checked.after,
    preserved: checked.preserved,
    invented: checked.invented,
    choices: checked.ranked.length,
  }));
  let finalRounds = 0;
  let finalVerdicts: Array<string | null> = [];
  let finalVerifierRungs: string[] = [];
  let lastReport = before;
  let copyAvailable = false;
  let flowAvailable = false;
  let finalizerAvailable = false;
  let passed = false;

  for (let round = 1; round <= MAX_FINAL_ROUNDS; round += 1) {
    finalRounds = round;

    const copied = await callRoleWithRecovery(env, "copydesk", current, current, deadline);
    const copyResult = await acceptNonWorsening(
      env, original, `copy desk ${round}`, copied?.text ?? null, current, checked, input.genre,
    );
    current = copyResult.text;
    checked = copyResult.checked;
    copyAvailable = copyResult.available;
    rolesCompleted += 1;

    const flowed = await callRoleWithRecovery(env, "readaloud", current, current, deadline);
    const flowResult = await acceptNonWorsening(
      env, original, `read aloud ${round}`, flowed?.text ?? null, current, checked, input.genre,
    );
    current = flowResult.text;
    checked = flowResult.checked;
    flowAvailable = flowResult.available;
    rolesCompleted += 1;

    const [report, changes] = await Promise.all([
      scoreWriting(env, current, input.genre),
      inventoryChanges(env, original, current),
    ]);
    lastReport = report;
    const verifierPacket = [
      "ORIGINAL:", original,
      "\nCURRENT:", current,
      "\nCHANGES TO CHECK:", JSON.stringify(changes),
      "\nDOCUMENT CHECKS:", JSON.stringify({
        register: report.register,
        shape: report.shape,
        score: report.score,
      }),
    ].join("\n");
    const firstVerifier = await callRole(env, "verify", verifierPacket, current, deadline);
    const secondVerifier = await callRole(
      env,
      "verify",
      verifierPacket,
      current,
      deadline,
      firstVerifier ? [firstVerifier.rung] : [],
      true,
    );
    finalVerdicts = [firstVerifier?.text ?? null, secondVerifier?.text ?? null];
    const verifierReplies = [firstVerifier, secondVerifier];
    finalVerifierRungs = [firstVerifier?.rung, secondVerifier?.rung]
      .filter((value): value is string => Boolean(value));
    rolesCompleted += 1;
    const verified = copyResult.available
      && flowResult.available
      && releaseReady(checked, report, finalVerdicts, finalVerifierRungs);
    console.log(JSON.stringify({
      event: "pipeline_verified",
      round,
      score: checked.after,
      preserved: checked.preserved,
      invented: checked.invented,
      registerFindings: report.register.findings.length,
      shapeFinding: report.shape.broetry,
      copyAvailable: copyResult.available,
      flowAvailable: flowResult.available,
      verifierPasses: finalVerdicts.map(verifierPassed),
      verifierRungs: finalVerifierRungs,
      independentVerifierRungs: new Set(finalVerifierRungs).size,
      verified,
    }));

    const finalPacket = [
      "ORIGINAL:", original,
      "\nCURRENT:", current,
      "\nVERIFIERS:", finalVerdicts.map((value) => value ?? "unavailable").join(" | "),
      "\nLOCAL SCORER:", scorerGuidance(report),
      "\nDOCUMENT CHECKS:", JSON.stringify({
        register: report.register,
        shape: report.shape,
        score: report.score,
      }),
      "\nCHANGES TO CHECK:", JSON.stringify(changes),
    ].join("\n");
    const approvingRungs = verified ? [] : verifierReplies
      .filter((reply): reply is NonNullable<typeof reply> => Boolean(reply && verifierPassed(reply.text)))
      .map((reply) => reply.rung);
    const finished = await callRoleWithRecovery(
      env,
      "finalize",
      finalPacket,
      current,
      deadline,
      approvingRungs,
      false,
    );
    rolesCompleted += 1;
    if (!finished) break;
    finalizerAvailable = true;

    if (finished.text !== current) {
      const finalCheck = await rankRewrites(env, original, { "fresh eyes": finished.text }, input.genre);
      if (finalCheck.preserved && !finalCheck.invented && finalCheck.after <= checked.after) {
        current = finished.text;
        checked = finalCheck;
        continue;
      }
      // A changed finalizer response is not an approval. Keep the last safe edit
      // and retry the finishing loop within its fixed budget.
      continue;
    }

    passed = verified;
    break;
  }

  if (!passed) {
    if (current !== original && checked.preserved && !checked.invented) {
      const after = await scoreWriting(env, current, input.genre);
      const warnings: string[] = [];
      if (!copyAvailable) warnings.push("the copy-editing pass was unavailable");
      if (!flowAvailable) warnings.push("the read-aloud pass was unavailable");
      if (after.score >= SCORE_GATE) warnings.push("the writing-score target was not reached");
      if (lastReport.register.findings.length > 0 || lastReport.shape.broetry) {
        warnings.push("a document-level writing check still needs review");
      }
      if (independentApprovals(finalVerdicts, finalVerifierRungs) < 2) {
        warnings.push("the two independent review checks did not both approve it");
      }
      if (!finalizerAvailable) warnings.push("the fresh-eyes pass was unavailable");
      const detail = warnings.length > 0
        ? warnings.join("; ")
        : "not every final quality check approved it";
      return {
        text: current,
        status: "rewritten_with_warnings",
        before,
        after,
        scoreChange: Math.round((after.score - before.score) * 10) / 10,
        factsPreserved: true,
        passedFinalChecks: false,
        independentModelChecks: independentApprovals(finalVerdicts, finalVerifierRungs),
        rolesCompleted: Math.min(8, rolesCompleted),
        finishingRounds: finalRounds,
        scorerVersion: env.SCORER_VERSION,
        durationMs: Date.now() - started,
        note: `This is the safest source-preserving edit the pipeline produced. Review it before publishing because ${detail}.`,
      };
    }
    return unchanged(
      original,
      "unchanged_verification_failed",
      before,
      started,
      env.SCORER_VERSION,
      Math.min(8, rolesCompleted),
      finalRounds,
      "Every changed version failed the hard source check, so the original comes back unchanged rather than risking an invented or dropped fact.",
    );
  }

  const after = await scoreWriting(env, current, input.genre);
  return {
    text: current,
    status: passed ? "rewritten" : "rewritten_with_warnings",
    before,
    after,
    scoreChange: Math.round((after.score - before.score) * 10) / 10,
    factsPreserved: checked.preserved && !checked.invented,
    passedFinalChecks: passed,
    independentModelChecks: independentApprovals(finalVerdicts, finalVerifierRungs),
    rolesCompleted: 8,
    finishingRounds: finalRounds,
    scorerVersion: env.SCORER_VERSION,
    durationMs: Date.now() - started,
    note: passed
      ? "Two independent model checks and the exact Zero Slop scorer approved this text."
      : "The deterministic source and writing checks approved this improvement, but the independent model reviewers did not fully agree. Review the diff before publishing.",
  };
}
