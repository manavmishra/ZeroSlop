import { env } from "cloudflare:workers";
import { describe, expect, it, vi } from "vitest";

import { callRole } from "../src/model";

describe("signed editor request in workerd", () => {
  it("constructs a native request and signs its exact body before reading an editor result", async () => {
    const output = "Maya will send the draft by Friday. Omar will review it before the team approves the release.";
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      // Node-only fetch stubs used to skip the Workers Request constructor,
      // hiding platform-specific request failures from the editorial tests.
      const request = new Request(input, init);
      expect(request.redirect).toBe("manual");
      const body = await request.text();
      expect(JSON.parse(body).noStore).toBe(true);
      const timestamp = request.headers.get("x-zero-slop-timestamp");
      const signature = request.headers.get("x-zero-slop-signature");
      expect(timestamp).toMatch(/^\d{13}$/);
      expect(signature).toMatch(/^[0-9a-f]{64}$/);
      const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(env.EDITOR_SHARED_SECRET),
        { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
      const bytes = Uint8Array.from(signature!.match(/../g)!, (pair) => Number.parseInt(pair, 16));
      expect(await crypto.subtle.verify("HMAC", key, bytes, new TextEncoder().encode(`${timestamp}.${body}`))).toBe(true);
      return Response.json({ rewrite: output, stored: false, provider: "workers-ai", model: "synthetic-editor" });
    });
    try {
      const result = await callRole(env, "complete",
        "It is important to note that Maya will send the draft by Friday. Omar will review it before the team approves the release.",
        { genre: "email" }, Date.now() + 5_000);
      expect(result?.text).toBe(output);
      expect(fetch).toHaveBeenCalledTimes(1);
    } finally {
      fetch.mockRestore();
    }
  });

  it("rejects a redirected editor response without forwarding the signed draft", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const request = new Request(input, init);
      expect(request.redirect).toBe("manual");
      return new Response(null, { status: 302, headers: { location: "https://example.invalid/editor" } });
    });
    try {
      expect(await callRole(env, "complete", "Maya owns the pricing draft.",
        { genre: "email" }, Date.now() + 5_000)).toBeNull();
      expect(fetch).toHaveBeenCalledTimes(1);
    } finally {
      fetch.mockRestore();
    }
  });
});
