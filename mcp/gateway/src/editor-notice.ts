export const OPENROUTER_NOTICE = "2026-11-11";
export const OPENROUTER_NOTICE_HEADER = "X-Zero-Slop-OpenRouter-Notice";
export const WEBSITE_ORIGINS = new Set(["https://zero-slop.ai", "https://www.zero-slop.ai"]);

export function hasCurrentOpenRouterNotice(request: Request): boolean {
  const origin = request.headers.get("origin");
  // External API and MCP submissions follow the published tool contract.
  if (origin === null) return true;
  if (WEBSITE_ORIGINS.has(origin)) return request.headers.get(OPENROUTER_NOTICE_HEADER) === OPENROUTER_NOTICE;
  // MCP admits some Origins by hostname. A noncanonical website Origin cannot
  // use that admission rule to bypass the notice on an older browser tab.
  try {
    const { hostname } = new URL(origin);
    return hostname !== "zero-slop.ai" && hostname !== "www.zero-slop.ai";
  } catch {
    return false;
  }
}
