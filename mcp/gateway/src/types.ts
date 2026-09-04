export type Genre = "general" | "social" | "email" | "research" | "professional";

export type WritingReport = {
  score: number;
  band: string;
  words: number;
  sentences: number;
  flaggedPhrases: number;
  sentenceVariety: "natural" | "too even";
  readability: "clear" | "needs work";
  punctuation: {
    dashes: number;
    emoji: number;
    hashtags: number;
  };
  highWeightFlags: number;
  shape: {
    measured: boolean;
    broetry: boolean;
    oneSentenceParagraphShare: number | null;
    longestFragmentRun: number | null;
  };
  register: {
    measured: boolean;
    words: number;
    checked: number;
    findings: Array<{
      name: string;
      rate: number;
      budget: number;
      found: number;
      quote: string;
    }>;
    twoPartContrasts: number;
    announcements: number;
  };
  flags: Array<{
    phrase: string;
    strength: number;
    issue: string;
    direction: string;
  }>;
};

export type RankedRewrite = {
  name: string;
  text: string;
  preserved: boolean;
  invented: boolean;
  before: number;
  after: number;
  ranked: Array<{
    name: string;
    after: number;
    preserved: boolean;
    invented: boolean;
  }>;
};

export type ChangeInventory = {
  original_words: number;
  rewrite_words: number;
  net: number;
  inserted_runs: string[];
  deleted_runs: string[];
  cut_emphasis: string[];
};

export type PipelineStatus =
  | "rewritten"
  | "rewritten_with_warnings"
  | "already_clear"
  | "unchanged_no_better_version"
  | "unchanged_verification_failed"
  | "unchanged_service_unavailable";

export type PipelineResult = {
  text: string;
  status: PipelineStatus;
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
};
