#!/usr/bin/env node
// Renders the GitHub repository social preview (1280x640).
//
// Usage: node growth/make-social-preview.mjs [outfile]
//
// The asset is deterministic, uses no network resources, and stays under
// GitHub's 1 MB recommendation. Upload the output in Settings → General →
// Social preview.

import { chromium } from "playwright-core";
import { readFile, writeFile } from "node:fs/promises";

const out = process.argv[2] ?? "assets/social-preview.png";
const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const logo = await readFile(new URL("../assets/logo/zero-slop-logo-primary.svg", import.meta.url));
const logoURL = `data:image/svg+xml;base64,${logo.toString("base64")}`;

const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {
    --ink: #141412;
    --paper: #FBFAF7;
    --panel: #ffffff;
    --line: #ddded7;
    --muted: #65655f;
    --rust: #C15732;
    --green: #17634F;
  }
  * { box-sizing: border-box; }
  body {
    width: 1280px;
    height: 640px;
    margin: 0;
    overflow: hidden;
    color: var(--ink);
    background: var(--paper);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  main {
    height: 100%;
    display: grid;
    grid-template-columns: 1fr 400px;
    gap: 70px;
    padding: 58px 72px 52px;
  }
  .left { display: flex; flex-direction: column; justify-content: space-between; }
  .brand { display: flex; align-items: center; gap: 14px; }
  .brand img { display: block; width: 290px; height: auto; }
  .eyebrow {
    display: inline-flex; align-items: center; gap: 9px;
    color: var(--green); font: 600 13px ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: .12em; text-transform: uppercase; margin-bottom: 20px;
  }
  .eyebrow::before {
    content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--green);
    box-shadow: 0 0 0 5px rgba(23,99,79,.1);
  }
  h1 {
    margin: 0; max-width: 690px; font-size: 69px; line-height: .99;
    letter-spacing: -.045em; font-weight: 760;
  }
  h1 em { color: var(--rust); font-style: normal; }
  .sub {
    max-width: 650px; margin-top: 24px; color: var(--muted);
    font-size: 21px; line-height: 1.42; letter-spacing: -.01em;
  }
  .install {
    width: fit-content; padding: 14px 18px; border: 1px solid var(--line);
    border-radius: 11px; background: var(--panel);
    color: var(--ink); font: 15px ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .install span { color: var(--green); }
  .proof {
    align-self: center; width: 400px; min-height: 452px; padding: 28px;
    border: 1px solid var(--line); border-radius: 24px;
    background: var(--panel);
    box-shadow: 0 18px 50px rgba(20,20,18,.06);
  }
  .proof-top {
    display: flex; align-items: center; justify-content: space-between;
    color: var(--muted); font: 12px ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: .1em; text-transform: uppercase;
  }
  .status { color: var(--green); }
  .score-row {
    display: grid; grid-template-columns: 1fr 56px 1fr;
    align-items: center; margin-top: 34px;
  }
  .score small {
    display: block; color: var(--muted); margin-bottom: 5px;
    font: 12px ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: .08em; text-transform: uppercase;
  }
  .score strong { font-size: 56px; letter-spacing: -.06em; font-weight: 680; }
  .score.before strong { color: var(--muted); }
  .score.after { text-align: right; }
  .score.after strong { color: var(--green); }
  .arrow { color: var(--rust); font-size: 25px; text-align: center; }
  .rail {
    height: 8px; margin: 30px 0 32px; border-radius: 99px;
    background: var(--line); overflow: hidden; position: relative;
  }
  .rail::before {
    content: ""; position: absolute; inset: 0 82% 0 0;
    background: var(--green); border-radius: inherit;
  }
  .check {
    display: flex; align-items: center; justify-content: space-between;
    padding: 17px 0; border-top: 1px solid var(--line); color: var(--muted);
    font: 14px ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .check b { color: var(--ink); font-weight: 600; }
  .tick {
    width: 23px; height: 23px; display: grid; place-items: center;
    border-radius: 50%; background: rgba(23,99,79,.1); color: var(--green);
    font: 700 13px ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .foot {
    display: flex; gap: 18px; margin-top: 22px; color: var(--muted);
    font: 12px ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .foot span + span::before { content: "·"; margin-right: 18px; color: var(--muted); }
</style>
</head>
<body>
  <main>
    <section class="left">
      <div class="brand"><img src="${logoURL}" alt="Zero Slop"></div>
      <div>
        <div class="eyebrow">Free, open-source Agent Skill</div>
        <h1>Find AI slop.<br><em>Keep the source intact.</em></h1>
        <p class="sub">Score the draft, edit with your existing assistant, then check names, numbers, links, and quotations locally.</p>
      </div>
      <div class="install"><span>$</span> npx skills add manavmishra/ZeroSlop --global</div>
    </section>
    <aside class="proof">
      <div class="proof-top"><span>Saved 18-draft replay</span><span class="status">verified</span></div>
      <div class="score-row">
        <div class="score before"><small>Draft</small><strong>76.3</strong></div>
        <div class="arrow">→</div>
        <div class="score after"><small>Edited</small><strong>12.8</strong></div>
      </div>
      <div class="rail"></div>
      <div class="check"><span>Source checks</span><b>18 / 18</b><i class="tick">✓</i></div>
      <div class="check"><span>Runtime dependencies</span><b>0</b><i class="tick">✓</i></div>
      <div class="check"><span>Local scorer</span><b>offline</b><i class="tick">✓</i></div>
      <div class="foot"><span>MIT</span><span>zero-slop.ai</span></div>
    </aside>
  </main>
</body>
</html>`;

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1280, height: 640 },
    deviceScaleFactor: 1,
  });
  await page.setContent(html);
  await page.locator(".brand img").evaluate(image => image.decode());
  const buffer = await page.screenshot({ type: "png" });
  await writeFile(out, buffer);
  console.log(`wrote ${out} (${(buffer.length / 1024).toFixed(0)} KB, 1280x640)`);
} finally {
  await browser.close();
}
