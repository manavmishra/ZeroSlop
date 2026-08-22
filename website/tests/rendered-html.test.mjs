import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);

async function render(pathname = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`https://zero-slop.ai${pathname}`, {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("renders the Zero Slop landing page and its primary journey", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Zero Slop \| Remove the AI accent from your writing<\/title>/i);
  assert.match(html, /Make AI writing sound like you\./);
  assert.match(html, /Score the slop\. Keep the meaning\./);
  assert.match(html, /npx(?:<!-- -->)? skills(?:<!-- -->)? add/i);
  assert.match(html, /href="https:\/\/github\.com\/manavmishra\/ZeroSlop"/i);
  assert.match(html, /id="how-it-works"/i);
  assert.match(html, /id="examples"/i);
  assert.match(html, /id="proof"/i);
  assert.match(html, /id="install"/i);
  assert.match(html, /One skill\. Your compatible agent\./i);
  assert.match(html, /Loop 1: Editorial delivery/i);
  assert.match(html, /Loop 2: Online learning/i);
  assert.match(html, /detector weights and save recurring human fixes/i);
  assert.match(html, /<ul[^>]+aria-label="Compatible agents"/i);
  assert.match(html, /Codex/i);
  assert.match(html, /Claude Code/i);
  assert.match(html, /Cursor/i);
  assert.match(html, /Gemini CLI/i);
  assert.match(html, /OpenCode/i);
  assert.match(html, /Warp/i);
  assert.match(html, /Zed/i);
  assert.match(html, /role="tablist"[^>]+aria-label="Writing format examples"/i);
  assert.match(html, /<button(?=[^>]+role="tab")(?=[^>]+aria-selected="true")[^>]*>/i);
  assert.match(html, /LinkedIn post/i);
  assert.match(html, /Blog intro/i);
  assert.match(html, /Strategy document/i);
  assert.match(html, /X thread/i);
  assert.match(html, /PowerPoint slide/i);
  assert.match(html, />Before</i);
  assert.match(html, />After</i);
  assert.match(html, /Context comes before a score./i);
  assert.doesNotMatch(html, /accuse slowly|confession|clusters convict/i);
  assert.doesNotMatch(html, /codex-preview|SkeletonPreview|react-loading-skeleton/i);
});

test("ships complete search, answer-engine, and social metadata", async () => {
  const html = await (await render()).text();

  assert.match(html, /<meta name="description" content="[^"]+"/i);
  assert.match(html, /<link rel="canonical" href="https:\/\/zero-slop\.ai\/?"/i);
  assert.match(html, /<meta property="og:title"/i);
  assert.match(html, /<meta property="og:description"/i);
  assert.match(html, /<meta property="og:image" content="https:\/\/zero-slop\.ai\/og\.png"/i);
  assert.match(html, /<meta name="twitter:card" content="summary_large_image"/i);
  assert.match(html, /"@type":"SoftwareApplication"/i);
  assert.match(html, /"@type":"FAQPage"/i);
  assert.match(html, /"isAccessibleForFree":true/i);
});

test("keeps the final UI accessible, responsive, and free of template residue", async () => {
  const [html, css, page, layout, packageJson] = await Promise.all([
    (await render()).text(),
    readFile(new URL("app/globals.css", projectRoot), "utf8"),
    readFile(new URL("app/page.tsx", projectRoot), "utf8"),
    readFile(new URL("app/layout.tsx", projectRoot), "utf8"),
    readFile(new URL("package.json", projectRoot), "utf8"),
  ]);

  assert.match(html, /<a[^>]+href="#main-content"[^>]*>Skip to content<\/a>/i);
  assert.match(html, /<main[^>]+id="main-content"/i);
  assert.match(html, /aria-label="Primary navigation"/i);
  assert.match(css, /:focus-visible/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /prefers-color-scheme:\s*dark/);
  assert.match(css, /min-height:\s*(?:calc\([^;]+\)|[0-9.]+dvh)/);
  assert.match(css, /@media\s*\(max-width:\s*767px\)/);

  const visibleCopy = html.replace(/<script[\s\S]*?<\/script>/gi, "");
  assert.doesNotMatch(visibleCopy, /[—–]/);
  assert.doesNotMatch(page, /_sites-preview|SkeletonPreview/);
  assert.doesNotMatch(layout, /Starter Project|codex-preview/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
});

test("publishes crawl controls and an AI-readable product summary", async () => {
  const [robots, sitemap, llms] = await Promise.all([
    readFile(new URL("public/robots.txt", projectRoot), "utf8"),
    readFile(new URL("public/sitemap.xml", projectRoot), "utf8"),
    readFile(new URL("public/llms.txt", projectRoot), "utf8"),
  ]);

  assert.match(robots, /User-agent:\s*\*/i);
  assert.match(robots, /Allow:\s*\//i);
  assert.match(robots, /Sitemap:\s*https:\/\/zero-slop\.ai\/sitemap\.xml/i);
  assert.match(sitemap, /<loc>https:\/\/zero-slop\.ai\/<\/loc>/i);
  assert.match(llms, /# Zero Slop/);
  assert.match(llms, /offline/i);
  assert.match(llms, /GitHub/i);
});
