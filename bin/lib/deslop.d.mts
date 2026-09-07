export type Genre = "general" | "social" | "email" | "research" | "professional";
export type ResultStatus = "rewritten" | "rewritten_with_warnings" | "already_clear" | "unchanged_no_better_version" | "unchanged_verification_failed" | "unchanged_service_unavailable";
export interface WritingReport {
  score: number; band: string; words: number; sentences: number; flaggedPhrases: number;
  sentenceVariety: "natural" | "too even"; readability: "clear" | "needs work";
  punctuation: { dashes: number; emoji: number; hashtags: number };
  highWeightFlags: number;
  shape: { measured: boolean; broetry: boolean; oneSentenceParagraphShare: number | null; longestFragmentRun: number | null };
  register: {
    measured: boolean; words: number; checked: number;
    findings: Array<{ name: string; rate: number; budget: number; found: number; quote: string }>;
    twoPartContrasts: number; announcements: number;
  };
  flags: Array<{ phrase: string; strength: number; issue: string; direction: string }>;
}
export interface PipelineResult {
  text: string; status: ResultStatus; before: WritingReport; after: WritingReport;
  scoreChange: number; factsPreserved: boolean; passedFinalChecks: boolean;
  independentModelChecks: number; modelRequests: number; rolesCompleted: number;
  finishingRounds: number; scorerVersion: string; durationMs: number; note: string;
}
export interface DeslopInput { text: string; genre?: Genre; audience?: string }
export interface DeslopOptions { signal?: AbortSignal; timeoutMs?: number; clientName?: string; clientVersion?: string }
export class DeslopError extends Error {
  code: string; httpStatus?: number; rpcCode?: number; retryAfterSeconds?: number;
  constructor(code: string, message: string, details?: Record<string, unknown>);
}
export const MCP_ENDPOINT: string;
export const GENRES: readonly Genre[];
export const RESULT_STATUSES: readonly ResultStatus[];
export function validateInput(input: DeslopInput): Required<Pick<DeslopInput, "text" | "genre">> & Pick<DeslopInput, "audience">;
export function validateResult(result: unknown): PipelineResult;
export function isApprovedResult(result: PipelineResult): boolean;
export function deslop(input: DeslopInput, options?: DeslopOptions): Promise<PipelineResult>;
