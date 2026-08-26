#!/usr/bin/env node
// Renders the GitHub repo social preview card (1280x640).
//
// GitHub exposes no API for repo social previews, so this only produces the
// file; uploading it is a manual step in Settings -> General -> Social preview.
//
// Usage: node scripts/make-social-preview.mjs [outfile]

import { chromium } from "playwright-core";
import { writeFile } from "node:fs/promises";

const out = process.argv[2] ?? "assets/social-preview.png";
const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

// Site palette, dark variant: background #17150e, paper #faf5e0, green #227B5B,
// violet #72528F. Kept in sync with ZSWebpage/app/globals.css by hand.
// Terracotta rust on paper white. The score is drawn as a measurement scale
// rather than a pair of coloured chips: the product measures writing, so the
// card should look like a measurement, not a promotion.
const RUST = "#b0442a";
const DRAFT = 77;
const EDITED = 14;

// Positions on a 0-100 axis, inset so the end dots never clip the track.
const pos = (n) => `${4 + (n / 100) * 92}%`;

const html = `<!doctype html>
<html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    width:1280px; height:640px; display:flex; flex-direction:column;
    justify-content:space-between; padding:60px 80px 56px;
    background:#ffffff; color:#1a1714;
    font-family:'Manrope',system-ui,sans-serif;
  }
  header { display:flex; justify-content:space-between; align-items:center; }
  .mark { display:flex; align-items:center; gap:12px; font-size:19px; font-weight:800;
          letter-spacing:.13em; text-transform:uppercase; color:${RUST}; }
  .mark i { width:11px; height:11px; background:${RUST}; border-radius:2px; display:block; }
  .site { font-family:'IBM Plex Mono',monospace; font-size:16px; color:#8a8178; }

  h1 { font-size:66px; font-weight:800; letter-spacing:-.033em; line-height:1.08; }
  h1 span { color:#a9a099; }

  .scale { margin-top:76px; }
  .track { position:relative; height:3px; background:#e9e4de; border-radius:2px; }
  .fill  { position:absolute; top:0; bottom:0; background:${RUST}; opacity:.16; border-radius:2px; }
  .node  { position:absolute; top:50%; transform:translate(-50%,-50%); }
  .node b { display:block; width:15px; height:15px; border-radius:50%; }
  .node.draft  b { background:#ffffff; border:3px solid #c8c1b9; }
  .node.edited b { background:${RUST}; box-shadow:0 0 0 6px rgba(176,68,42,.13); }
  .node u {
    position:absolute; left:50%; transform:translateX(-50%); top:30px;
    text-decoration:none; white-space:nowrap; text-align:center;
  }
  .node u em { display:block; font-family:'IBM Plex Mono',monospace; font-size:12px;
               letter-spacing:.15em; text-transform:uppercase; color:#8a8178;
               font-style:normal; margin-bottom:3px; }
  .node u strong { font-size:38px; font-weight:600; letter-spacing:-.02em; line-height:1; }
  .node.draft u strong  { color:#a9a099; }
  .node.edited u strong { color:${RUST}; }
  .axis { display:flex; justify-content:space-between; font-family:'IBM Plex Mono',monospace;
          font-size:12px; color:#c6bfb7; margin-top:96px; }

  footer { display:flex; justify-content:space-between; align-items:baseline;
           border-top:1px solid #ece7e1; padding-top:20px; }
  .meta { font-family:'IBM Plex Mono',monospace; font-size:15px; color:#8a8178; }
  .meta b { color:#1a1714; font-weight:500; }
</style></head>
<body>
  <header>
    <div class="mark"><i></i>Zero Slop</div>
    <div class="site">zero-slop.ai</div>
  </header>

  <div>
    <h1>Less slop, more pop.<br><span>No rewrites.</span></h1>
    <div class="scale">
      <div class="track">
        <div class="fill" style="left:${pos(EDITED)};right:${100 - parseFloat(pos(DRAFT))}%"></div>
        <div class="node draft"  style="left:${pos(DRAFT)}"><b></b><u><em>draft</em><strong>${DRAFT}</strong></u></div>
        <div class="node edited" style="left:${pos(EDITED)}"><b></b><u><em>edited</em><strong>${EDITED}</strong></u></div>
      </div>
      <div class="axis"><span>0</span><span>writing score</span><span>100</span></div>
    </div>
  </div>

  <footer>
    <div class="meta"><b>Agent Skill</b> &middot; MIT &middot; zero dependencies &middot; runs locally</div>
    <div class="meta">npx skills add manavmishra/ZeroSlop</div>
  </footer>
</body></html>`;

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 640 }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  const buffer = await page.screenshot({ type: "png" });
  await writeFile(out, buffer);
  console.log(`wrote ${out} (${(buffer.length / 1024).toFixed(0)} KB, 1280x640)`);
} finally {
  await browser.close();
}
