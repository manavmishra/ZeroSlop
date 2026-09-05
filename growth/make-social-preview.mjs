#!/usr/bin/env node
// Renders the GitHub repository social preview (1280x640).
//
// Usage: node growth/make-social-preview.mjs [outfile]
//
// The asset is deterministic, uses no network resources, and stays under
// GitHub's 1 MB recommendation. Upload the output in Settings → General →
// Social preview.

import { chromium } from "playwright-core";
import { writeFile } from "node:fs/promises";

const out = process.argv[2] ?? "assets/social-preview.png";
const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {
    --ink: #f7f0dd;
    --paper: #17150f;
    --panel: #211e17;
    --line: #3b362a;
    --muted: #aaa18f;
    --rust: #d76545;
    --green: #66c69a;
  }
  * { box-sizing: border-box; }
  body {
    width: 1280px;
    height: 640px;
    margin: 0;
    overflow: hidden;
    color: var(--ink);
    background:
      radial-gradient(circle at 79% 17%, rgba(167,139,195,.15), transparent 27%),
      linear-gradient(rgba(255,255,255,.024) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.024) 1px, transparent 1px),
      var(--paper);
    background-size: auto, 40px 40px, 40px 40px, auto;
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
  .mark {
    width: 31px; height: 31px; border: 2px solid var(--rust);
    border-radius: 8px; position: relative; transform: rotate(45deg);
  }
  .mark::before {
    content: ""; position: absolute; width: 13px; height: 2px;
    background: var(--rust); left: 7px; top: 7px;
    box-shadow: 0 11px 0 var(--rust); transform: rotate(-45deg);
  }
  .wordmark {
    font-size: 20px; line-height: 1; font-weight: 750;
    letter-spacing: .16em; text-transform: uppercase;
  }
  .eyebrow {
    display: inline-flex; align-items: center; gap: 9px;
    color: var(--green); font: 600 13px ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: .12em; text-transform: uppercase; margin-bottom: 20px;
  }
  .eyebrow::before {
    content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--green);
    box-shadow: 0 0 0 5px rgba(102,198,154,.12);
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
    border-radius: 11px; background: rgba(33,30,23,.78);
    color: #ddd4c0; font: 15px ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .install span { color: var(--green); }
  .proof {
    align-self: center; width: 400px; min-height: 452px; padding: 28px;
    border: 1px solid var(--line); border-radius: 24px;
    background: linear-gradient(145deg, rgba(39,35,27,.95), rgba(27,25,19,.94));
    box-shadow: 0 28px 70px rgba(0,0,0,.24);
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
  .score.before strong { color: #b0a895; }
  .score.after { text-align: right; }
  .score.after strong { color: var(--green); }
  .arrow { color: var(--rust); font-size: 25px; text-align: center; }
  .rail {
    height: 8px; margin: 30px 0 32px; border-radius: 99px;
    background: #39342a; overflow: hidden; position: relative;
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
    border-radius: 50%; background: rgba(102,198,154,.12); color: var(--green);
    font: 700 13px ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .foot {
    display: flex; gap: 18px; margin-top: 22px; color: var(--muted);
    font: 12px ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .foot span + span::before { content: "·"; margin-right: 18px; color: #5f5849; }
</style>
</head>
<body>
  <main>
    <section class="left">
      <div class="brand"><i class="mark"></i><span class="wordmark">Zero Slop</span></div>
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
  const buffer = await page.screenshot({ type: "png" });
  await writeFile(out, buffer);
  console.log(`wrote ${out} (${(buffer.length / 1024).toFixed(0)} KB, 1280x640)`);
} finally {
  await browser.close();
}
