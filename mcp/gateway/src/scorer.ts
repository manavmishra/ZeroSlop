import { z } from "zod";

import { readBoundedJson } from "./bounded-json";
import type { ChangeInventory, Genre, RankedRewrite, WritingReport } from "./types";

type ScorerPath = "/report" | "/rank" | "/delta";
const MAX_SCORER_RESPONSE_BYTES = 2 * 1024 * 1024;
const SCORER_TIMEOUT_MS = 8_000;

const nonnegativeInteger = z.number().int().nonnegative();

export const writingReportSchema = z.object({
  score: z.number().min(0).max(100),
  band: z.string().min(1).max(80),
  words: nonnegativeInteger,
  sentences: nonnegativeInteger,
  flaggedPhrases: nonnegativeInteger,
  sentenceVariety: z.enum(["natural", "too even"]),
  readability: z.enum(["clear", "needs work"]),
  punctuation: z.object({
    dashes: nonnegativeInteger,
    emoji: nonnegativeInteger,
    hashtags: nonnegativeInteger,
  }),
  highWeightFlags: nonnegativeInteger,
  shape: z.object({
    measured: z.boolean(),
    broetry: z.boolean(),
    oneSentenceParagraphShare: z.number().min(0).max(1).nullable(),
    longestFragmentRun: nonnegativeInteger.nullable(),
  }),
  register: z.object({
    measured: z.boolean(),
    words: nonnegativeInteger,
    checked: nonnegativeInteger,
    findings: z.array(z.object({
      name: z.string().max(160),
      rate: z.number().nonnegative(),
      budget: z.number().nonnegative(),
      found: nonnegativeInteger,
      quote: z.string().max(1_000),
    })).max(1_000),
    twoPartContrasts: nonnegativeInteger,
    announcements: nonnegativeInteger,
  }),
  flags: z.array(z.object({
    phrase: z.string().max(1_000),
    strength: z.number().nonnegative(),
    issue: z.string().max(2_000),
    direction: z.string().max(2_000),
  })).max(5_000),
}).passthrough();

const rankedRewriteSchema = z.object({
  name: z.string().min(1).max(160),
  text: z.string(),
  preserved: z.boolean(),
  invented: z.boolean(),
  before: z.number().min(0).max(100),
  after: z.number().min(0).max(100),
  ranked: z.array(z.object({
    name: z.string().min(1).max(160),
    after: z.number().min(0).max(100),
    preserved: z.boolean(),
    invented: z.boolean(),
  })).max(32),
}).passthrough();

const changeInventorySchema = z.object({
  original_words: nonnegativeInteger,
  rewrite_words: nonnegativeInteger,
  net: z.number().int(),
  inserted_runs: z.array(z.string().max(2_000)).max(2_000),
  deleted_runs: z.array(z.string().max(2_000)).max(2_000),
  cut_emphasis: z.array(z.string().max(2_000)).max(2_000),
}).passthrough();

const scorerHealthSchema = z.object({
  ok: z.boolean(),
  scorerVersion: z.string().min(1).max(80),
}).passthrough();

async function callScorer<T>(
  env: Env,
  path: ScorerPath,
  payload: unknown,
  schema: z.ZodType<T>,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), SCORER_TIMEOUT_MS);
  try {
    const response = await env.SCORER.fetch(`https://zero-slop-scorer${path}`, {
      method: "POST",
      signal: controller.signal,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`scorer_${response.status}`);
    }
    const parsed = schema.safeParse(await readBoundedJson(response, MAX_SCORER_RESPONSE_BYTES));
    if (!parsed.success) throw new Error("scorer_invalid_response");
    return parsed.data;
  } finally {
    clearTimeout(timer);
  }
}

export function scoreWriting(env: Env, text: string, genre: Genre): Promise<WritingReport> {
  return callScorer(env, "/report", { text, genre }, writingReportSchema);
}

export function rankRewrites(
  env: Env,
  original: string,
  candidates: Record<string, string>,
  genre: Genre,
): Promise<RankedRewrite> {
  return callScorer(env, "/rank", { original, candidates, genre }, rankedRewriteSchema);
}

export function inventoryChanges(
  env: Env,
  original: string,
  rewrite: string,
): Promise<ChangeInventory> {
  return callScorer(env, "/delta", { original, rewrite }, changeInventorySchema);
}

export async function scorerHealth(env: Env): Promise<{ ok: boolean; scorerVersion: string }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), SCORER_TIMEOUT_MS);
  try {
    const response = await env.SCORER.fetch("https://zero-slop-scorer/health", { signal: controller.signal });
    if (!response.ok) throw new Error(`scorer_${response.status}`);
    const parsed = scorerHealthSchema.safeParse(await readBoundedJson(response, 16 * 1024));
    if (!parsed.success) throw new Error("scorer_invalid_response");
    return parsed.data;
  } finally {
    clearTimeout(timer);
  }
}
