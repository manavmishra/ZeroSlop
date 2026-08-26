#!/usr/bin/env node
// Renders the submission logo set from the site favicon.
//
// Directory submissions (Product Hunt, AlternativeTo, SourceForge, the Anthropic
// plugin directory, every AI index) all ask for a square PNG at 512x512 or
// larger with a transparent background. The repo had only favicon.svg, two
// 1200x630 OG jpegs and a 1500x800 demo, so there was nothing to upload.
//
// Two shapes, because directories place logos differently:
//   logo-<n>.png       the rounded plate, alpha outside the corner radius.
//                      Use wherever the logo sits on the directory's own card.
//   logo-mark-<n>.png  the glyph alone on full transparency, no plate.
//                      Use wherever the directory composites onto its own
//                      background and a dark plate would fight it.
//
// Chrome rasterises the same SVG the site serves, so the mark cannot drift from
// the favicon. omitBackground gives real alpha rather than a matted white.
//
// Usage: node growth/make-logo.mjs [outdir]

import { chromium } from "playwright-core";
import { readFile, writeFile, mkdir } from "node:fs/promises";

const outDir = process.argv[2] ?? "assets/logo";
const sizes = [512, 1024];
const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const svg = await readFile("ZSWebpage/public/favicon.svg", "utf8");

// The plate is the first <rect> in the favicon. Dropping it leaves the "Z" and
// the strike-through bar, which is the mark proper.
//
// The Z is #fffdf6 because it sits on the dark plate. Off the plate it is
// composited onto whatever the directory card uses, which is nearly always
// white, so it has to be recoloured to the plate's own ink or the mark renders
// as a bar floating over nothing.
const markOnly = svg
  .replace(/<rect width="64" height="64"[^>]*\/>\s*/, "")
  .replace(/fill="#fffdf6"/, 'fill="#12100c"');

// The glyph is inset within the 64-unit plate. Without the plate that inset
// reads as stray padding, so the mark-only variant is scaled up — but only as
// far as the strike-through bar allows, since it is the widest element and its
// rounded ends clip before the Z does.
const MARK_ZOOM = 1.12;

function page(markup, size, zoom = 1) {
  return `<!doctype html>
<html><head><meta charset="utf-8"><style>
  * { margin:0; padding:0; }
  html, body { width:${size}px; height:${size}px; background:transparent; }
  svg { width:${size}px; height:${size}px; display:block; transform:scale(${zoom}); transform-origin:center; }
</style></head><body>${markup}</body></html>`;
}

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
try {
  for (const size of sizes) {
    for (const [name, markup, zoom] of [
      [`logo-${size}.png`, svg, 1],
      [`logo-mark-${size}.png`, markOnly, MARK_ZOOM],
    ]) {
      const tab = await browser.newPage({
        viewport: { width: size, height: size },
        deviceScaleFactor: 1,
      });
      await tab.setContent(page(markup, size, zoom), { waitUntil: "load" });
      const buffer = await tab.screenshot({ type: "png", omitBackground: true });
      await writeFile(`${outDir}/${name}`, buffer);
      await tab.close();
      console.log(`wrote ${outDir}/${name} (${(buffer.length / 1024).toFixed(0)} KB, ${size}x${size})`);
    }
  }
} finally {
  await browser.close();
}
