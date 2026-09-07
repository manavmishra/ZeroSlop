export const GENRES = [
  "general",
  "social",
  "email",
  "research",
  "professional",
] as const;
export type Genre = (typeof GENRES)[number];
export const CLIENT_VERSION = "2.10.0";

export const STATUS_LABELS = {
  rewritten: "Edit completed",
  rewritten_with_warnings: "Review required",
  already_clear: "Already clear",
  unchanged_no_better_version: "Original retained",
  unchanged_verification_failed: "Source checks did not pass",
  unchanged_service_unavailable: "Editor unavailable",
} as const;

// A literal code block prevents draft Markdown from loading external images or
// turning arbitrary links into clickable UI. Adapt the fence to its contents.
export function literalText(text: string): string {
  const longest = Math.max(
    2,
    ...(text.match(/`+/g) || []).map((match) => match.length),
  );
  const fence = "`".repeat(longest + 1);
  return `${fence}text\n${text}\n${fence}`;
}

export function validateDraft(
  text: string,
  genre: string,
  audience: string,
): { text: string; genre: Genre; audience?: string } {
  const draft = text.trim();
  if (!draft) throw new Error("Select or enter a draft first.");
  if (exceedsCodePoints(draft, 20_000))
    throw new Error("Use a selection of 20,000 characters or fewer.");
  if (!GENRES.includes(genre as Genre))
    throw new Error("Choose a supported writing type.");
  if (exceedsCodePoints(audience.trim(), 200))
    throw new Error("Keep the audience description within 200 characters.");
  return {
    text: draft,
    genre: genre as Genre,
    ...(audience.trim() ? { audience: audience.trim() } : {}),
  };
}

function exceedsCodePoints(text: string, maximum: number): boolean {
  let count = 0;
  const points = text[Symbol.iterator]();
  while (!points.next().done) {
    count += 1;
    if (count > maximum) return true;
  }
  return false;
}

export function reviewMarkdown(
  original: string,
  result: { text: string; status: keyof typeof STATUS_LABELS; note: string },
): string {
  return `# ${STATUS_LABELS[result.status]}\n\n${literalText(result.note)}\n\n## Edited text\n\n${literalText(result.text)}\n\n## Original\n\n${literalText(original)}`;
}

export async function editDraft<T>(
  text: string,
  genre: string,
  audience: string,
  signal: AbortSignal,
  editor: (
    input: { text: string; genre: Genre; audience?: string },
    options: {
      signal: AbortSignal;
      timeoutMs: number;
      clientName: string;
      clientVersion: string;
    },
  ) => Promise<T>,
): Promise<T> {
  const input = validateDraft(text, genre, audience);
  if (signal.aborted) throw new Error("Editing was cancelled.");
  return editor(input, {
    signal,
    timeoutMs: 75_000,
    clientName: "zero-slop-raycast",
    clientVersion: CLIENT_VERSION,
  });
}
