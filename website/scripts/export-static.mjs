import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
const clientDirectory = new URL("../dist/client/", import.meta.url);
const staticDirectory = new URL("../dist/static/", import.meta.url);
const workerUrl = new URL("../dist/server/index.js", import.meta.url);
workerUrl.searchParams.set("export", `${process.pid}-${Date.now()}`);

const { default: worker } = await import(workerUrl.href);
const fetchWorker = typeof worker === "function" ? worker : worker.fetch.bind(worker);
const response = await fetchWorker(
  new Request("https://zero-slop.ai/", { headers: { accept: "text/html" } }),
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

if (!response.ok) {
  throw new Error(`Static export failed with HTTP ${response.status}`);
}

let html = await response.text();
html = html
  .replace(/<link\b(?=[^>]*\brel=["']modulepreload["'])[^>]*>\s*/gi, "")
  .replace(
    /<script\b(?![^>]*(?:type=["']application\/ld\+json["']|data-zero-slop-ui\b))[^>]*>[\s\S]*?<\/script>\s*/gi,
    "",
  );

if (/<script[^>]+src=/i.test(html) || /rel=["']modulepreload["']/i.test(html)) {
  throw new Error("Static export still contains framework JavaScript");
}
if (!/data-zero-slop-ui/i.test(html)) {
  throw new Error("Static export is missing the interaction layer");
}

await rm(staticDirectory, { recursive: true, force: true });
await mkdir(staticDirectory, { recursive: true });
await cp(clientDirectory, staticDirectory, { recursive: true });
await rm(new URL("_next/static/chunks/", staticDirectory), { recursive: true, force: true });
await writeFile(new URL("index.html", staticDirectory), html, "utf8");

const exportedHtml = await readFile(new URL("index.html", staticDirectory), "utf8");
if (!exportedHtml.startsWith("<!DOCTYPE html>")) {
  throw new Error("Static export is missing its document type");
}
