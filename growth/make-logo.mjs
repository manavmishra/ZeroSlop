#!/usr/bin/env node
// Renders the Zero Slop logo from the repository-owned vector source.
//
// The 300px exports use the established black Z and rust slash. The SVG is
// shared with the README animation, so its geometry and colors cannot drift.
//
//   logo-300.png       black/rust mark on pure white, exact 300x300 canvas.
//   logo-mark-300.png  same mark with a transparent background.
//
// --all also regenerates the historical 512px and 1024px directory assets:
// dark rounded plate for logo-<n>.png, transparent for logo-mark-<n>.png.
// Without --all, those existing files are left untouched.
//
// Requires playwright-core and Chrome; no network access or remote fonts.
// Usage: node growth/make-logo.mjs [outdir] [--all]
// Optional ZERO_SLOP_NODE_MODULES points to an existing dependency directory.

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const dependencyRoot = process.env.ZERO_SLOP_NODE_MODULES;
const { chromium } = await import(dependencyRoot
  ? pathToFileURL(resolve(dependencyRoot, "playwright-core/index.mjs")).href
  : "playwright-core");
const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = resolve(process.argv.slice(2).find((arg) => arg !== "--all")
  ?? resolve(repoRoot, "assets/logo"));
const sizes = process.argv.includes("--all") ? [300, 512, 1024] : [300];
const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const markOnly = await readFile(resolve(repoRoot, "assets/logo/logo-mark.svg"), "utf8");

const darkPlate = markOnly
  .replace(/(<path\b[^>]*fill=")#12100c"/, '$1#fffdf6"')
  .replace(/(<svg\b[^>]*>)/, '$1<rect width="64" height="64" rx="17" fill="#12100c"/>')
  .replace(' transform="translate(-3.84 -3.84) scale(1.12)"', "");

function page(markup, size, background = "transparent") {
  return `<!doctype html>
<html><head><meta charset="utf-8"><style>
  * { margin:0; padding:0; }
  html, body { width:${size}px; height:${size}px; background:${background}; }
  svg { width:${size}px; height:${size}px; display:block; }
</style></head><body>${markup}</body></html>`;
}

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
try {
  for (const size of sizes) {
    for (const [name, markup, background] of [
      [`logo-${size}.png`, size === 300 ? markOnly : darkPlate, size === 300 ? "#ffffff" : "transparent"],
      [`logo-mark-${size}.png`, markOnly, "transparent"],
    ]) {
      const tab = await browser.newPage({
        viewport: { width: size, height: size },
        deviceScaleFactor: 1,
      });
      await tab.setContent(page(markup, size, background), { waitUntil: "load" });
      const buffer = await tab.screenshot({ type: "png", omitBackground: true });
      await writeFile(`${outDir}/${name}`, buffer);
      await tab.close();
      console.log(`wrote ${outDir}/${name} (${(buffer.length / 1024).toFixed(0)} KB, ${size}x${size})`);
    }
  }
} finally {
  await browser.close();
}
