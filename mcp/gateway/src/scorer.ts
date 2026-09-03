import type { ChangeInventory, Genre, RankedRewrite, WritingReport } from "./types";

type ScorerPath = "/report" | "/rank" | "/delta";

async function callScorer<T>(env: Env, path: ScorerPath, payload: unknown): Promise<T> {
  const response = await env.SCORER.fetch(`https://zero-slop-scorer${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`scorer_${response.status}`);
  }
  return response.json<T>();
}

export function scoreWriting(env: Env, text: string, genre: Genre): Promise<WritingReport> {
  return callScorer(env, "/report", { text, genre });
}

export function rankRewrites(
  env: Env,
  original: string,
  candidates: Record<string, string>,
  genre: Genre,
): Promise<RankedRewrite> {
  return callScorer(env, "/rank", { original, candidates, genre });
}

export function inventoryChanges(
  env: Env,
  original: string,
  rewrite: string,
): Promise<ChangeInventory> {
  return callScorer(env, "/delta", { original, rewrite });
}

export async function scorerHealth(env: Env): Promise<{ ok: boolean; scorerVersion: string }> {
  const response = await env.SCORER.fetch("https://zero-slop-scorer/health");
  if (!response.ok) throw new Error(`scorer_${response.status}`);
  return response.json<{ ok: boolean; scorerVersion: string }>();
}
