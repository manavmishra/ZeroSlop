#!/usr/bin/env node
// Renders the lightweight product demonstration used above the README fold.
//
// Usage: node scripts/make-readme-gif.mjs [outfile]
//
// The writing scores and four flags below are real output from:
//   python3 scripts/slopscore.py --explain
// Keep the source, rewrite, counts, and score labels in sync.

import { chromium } from "playwright-core";
import sharp from "sharp";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const out = resolve(process.argv[2] ?? "assets/zero-slop-demo.gif");
const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const W = 1100;
const H = 650;
const source =
  "We're thrilled to announce that our team has leveraged cutting-edge machine learning to deliver a seamless onboarding experience, reducing setup time by 40%.";
const rewrite = "We used machine learning to reduce onboarding setup time by 40%.";
const words = rewrite.split(" ");

const flags = [
  ["We're thrilled to", "canned opener"],
  ["leveraged", "promotional verb"],
  ["cutting-edge", "unsupported hype"],
  ["seamless", "promotional claim"],
];

const timeline = [
  { phase: "scan", flags: 0, delay: 1150 },
  { phase: "scan", flags: 1, delay: 700 },
  { phase: "scan", flags: 2, delay: 700 },
  { phase: "scan", flags: 3, delay: 700 },
  { phase: "scan", flags: 4, delay: 2100 },
  { phase: "cut", sweep: 4, delay: 350 },
  { phase: "cut", sweep: 25, delay: 350 },
  { phase: "cut", sweep: 48, delay: 350 },
  { phase: "cut", sweep: 72, delay: 350 },
  { phase: "cut", sweep: 96, delay: 800 },
  { phase: "edit", words: 2, delay: 500 },
  { phase: "edit", words: 4, delay: 500 },
  { phase: "edit", words: 6, delay: 500 },
  { phase: "edit", words: 9, delay: 1800 },
  { phase: "verify", checks: 1, delay: 650 },
  { phase: "verify", checks: 2, delay: 650 },
  { phase: "verify", checks: 3, delay: 2100 },
  { phase: "done", delay: 3100 },
];

const escapeHtml = (value) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");

function flaggedSource(active) {
  let html = escapeHtml(source);
  for (const [phrase] of flags.slice(0, active)) {
    html = html.replace(
      escapeHtml(phrase),
      `<mark>${escapeHtml(phrase)}</mark>`,
    );
  }
  return html;
}

function phaseRail(phase) {
  const phases = ["scan", "edit", "verify"];
  const normalized = phase === "cut" ? "edit" : phase;
  const current = normalized === "done" ? 3 : phases.indexOf(normalized);
  return phases
    .map((name, index) => {
      const state = index < current ? "passed" : index === current ? "active" : "";
      const label = name[0].toUpperCase() + name.slice(1);
      return `<span class="step ${state}"><i>0${index + 1}</i>${label}</span>`;
    })
    .join("");
}

function frameMarkup(state) {
  const activeFlags = state.flags ?? 4;
  const isScan = state.phase === "scan";
  const isCut = state.phase === "cut";
  const isDone = state.phase === "done";
  const editing = state.phase === "edit";
  const verifying = state.phase === "verify";
  const visibleWords = editing ? words.slice(0, state.words).join(" ") : rewrite;
  const score = isScan ? (activeFlags === 4 ? "99.3" : "—") : isCut ? "99.3" : isDone ? "9.5" : "…";
  const scoreClass = isDone ? "clear" : (isScan && activeFlags === 4) || isCut ? "heavy" : "";
  const headline = isScan
    ? activeFlags === 4
      ? "Four phrases are doing no work."
      : "Reading the draft…"
    : isCut
      ? "The Zero Cut"
      : editing
      ? "Cut the posture. Keep the result."
      : verifying
        ? "Check the edit against the source."
        : "Clearer writing. Same result.";

  const editor = isScan
    ? `<p class="copy source">${flaggedSource(activeFlags)}</p>`
    : isCut
      ? `<p class="copy source cut-copy">${flaggedSource(activeFlags)}</p><i class="zero-cut" style="--cut:${state.sweep}%"><span>ZERO CUT</span></i>`
      : `<p class="copy rewrite">${escapeHtml(visibleWords)}${editing && state.words < words.length ? '<i class="cursor"></i>' : ""}</p>`;

  const flagRows = flags
    .map(([phrase, reason], index) => {
      const visible = index < activeFlags;
      return `<li class="${visible ? "visible" : ""}"><span>${escapeHtml(phrase)}</span><small>${reason}</small></li>`;
    })
    .join("");

  const checks = [
    ["40%", "held"],
    ["Added names · numbers", "none"],
    ["Meaning review", "passed"],
  ]
    .map(([name, result], index) => {
      const visible = verifying ? index < state.checks : isDone;
      return `<li class="check ${visible ? "visible" : ""}"><span><b>✓</b> ${name}</span><small>${result}</small></li>`;
    })
    .join("");

  const panel = isScan || isCut
    ? `<div class="findings"><div class="panel-label">Exact flags</div><ul>${flagRows}</ul></div>`
    : `<div class="findings"><div class="panel-label">Source check</div><ul>${checks}</ul></div>`;

  return `
    <header>
      <div class="brand"><i class="mark"></i><strong>ZERO SLOP</strong></div>
      <div class="file">launch-post.md</div>
      <div class="local"><i></i> local checks</div>
    </header>
    <div class="rail">${phaseRail(state.phase)}</div>
    <main>
      <section class="workspace">
        <div class="eyebrow">${isScan ? "Draft" : isCut ? "Signature pass" : "Edit"}</div>
        <h1>${headline}</h1>
        <div class="document">${editor}</div>
      </section>
      <aside>
        <div class="score ${scoreClass}">
          <span>writing score</span>
          <strong>${score}</strong>
          <small>${isDone ? "clear" : ((isScan && activeFlags === 4) || isCut) ? "major rewrite" : "lower is better"}</small>
        </div>
        ${panel}
      </aside>
    </main>
    <footer>
      <span>Score → edit → verify</span>
      <code><b>$</b> npx skills add manavmishra/ZeroSlop --global</code>
      <span>zero-slop.ai</span>
    </footer>
  `;
}

const pageHtml = `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {
    --ink: #f6efdc;
    --paper: #17150f;
    --panel: #211e17;
    --line: #3a352a;
    --muted: #aaa18e;
    --rust: #db704f;
    --green: #65c89b;
    --amber: #efbd62;
  }
  * { box-sizing: border-box; }
  body {
    width: ${W}px; height: ${H}px; margin: 0; overflow: hidden;
    background:
      radial-gradient(circle at 88% 5%, rgba(114,82,143,.14), transparent 28%),
      var(--paper);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  #stage { width: 100%; height: 100%; display: grid; grid-template-rows: 62px 52px 1fr 62px; }
  header, footer { display: flex; align-items: center; padding: 0 38px; }
  header { border-bottom: 1px solid var(--line); }
  .brand { display: flex; align-items: center; gap: 11px; }
  .brand strong { font-size: 13px; letter-spacing: .16em; }
  .mark {
    display: block; width: 22px; height: 22px; border: 2px solid var(--rust);
    border-radius: 6px; transform: rotate(45deg);
  }
  .file {
    margin: auto; color: var(--muted);
    font: 12px ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .local {
    display: flex; align-items: center; gap: 8px; color: var(--green);
    font: 11px ui-monospace, SFMono-Regular, Menlo, monospace; text-transform: uppercase;
    letter-spacing: .08em;
  }
  .local i { width: 7px; height: 7px; border-radius: 50%; background: var(--green); }
  .rail { display: flex; align-items: center; gap: 30px; padding: 0 38px; border-bottom: 1px solid var(--line); }
  .step { color: #686252; font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; text-transform: uppercase; letter-spacing: .08em; }
  .step i { margin-right: 7px; font-style: normal; }
  .step.active { color: var(--ink); }
  .step.active i { color: var(--rust); }
  .step.passed { color: var(--green); }
  main { display: grid; grid-template-columns: 1fr 320px; min-height: 0; }
  .workspace { padding: 38px 46px; border-right: 1px solid var(--line); }
  .eyebrow {
    color: var(--rust); font: 11px ui-monospace, SFMono-Regular, Menlo, monospace;
    text-transform: uppercase; letter-spacing: .13em; margin-bottom: 10px;
  }
  h1 { margin: 0; font-size: 29px; line-height: 1.1; letter-spacing: -.028em; font-weight: 670; }
  .document {
    display: flex; align-items: center; min-height: 228px; margin-top: 26px;
    padding: 30px 33px; background: #1e1b15; border: 1px solid var(--line);
    border-radius: 15px; box-shadow: 0 18px 45px rgba(0,0,0,.16);
    position: relative; overflow: hidden;
  }
  .copy { margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: 25px; line-height: 1.55; color: #e9e0cc; }
  mark {
    color: inherit; background: rgba(219,112,79,.14); border-bottom: 2px solid var(--rust);
    padding: 1px 2px; border-radius: 3px;
  }
  .rewrite { color: var(--ink); font-size: 29px; line-height: 1.48; }
  .cut-copy { opacity: .42; filter: saturate(.7); }
  .zero-cut {
    position: absolute; left: var(--cut); top: -42px; width: 3px; height: 330px;
    background: var(--rust); box-shadow: -16px 0 32px rgba(101,200,155,.18), 0 0 24px rgba(219,112,79,.7);
    transform: rotate(13deg); transform-origin: center; z-index: 3;
  }
  .zero-cut::after {
    content: ""; position: absolute; width: 2px; height: 100%; left: -17px; top: 0;
    background: var(--green); opacity: .72;
  }
  .zero-cut span {
    position: absolute; left: 11px; top: 58px; padding: 5px 7px;
    border-radius: 5px; background: var(--rust); color: #17150f;
    font: 800 8px ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: .12em; white-space: nowrap; transform: rotate(-13deg);
  }
  .cursor { display: inline-block; width: 2px; height: 28px; margin-left: 5px; vertical-align: -4px; background: var(--rust); }
  aside { padding: 36px 30px 26px; background: rgba(33,30,23,.5); }
  .score { padding-bottom: 28px; border-bottom: 1px solid var(--line); }
  .score span, .panel-label {
    display: block; color: var(--muted); font: 11px ui-monospace, SFMono-Regular, Menlo, monospace;
    text-transform: uppercase; letter-spacing: .1em;
  }
  .score strong { display: block; margin: 5px 0 0; font-size: 62px; line-height: 1; letter-spacing: -.06em; color: #b1a996; }
  .score small { color: var(--muted); font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; }
  .score.heavy strong { color: var(--rust); }
  .score.clear strong { color: var(--green); }
  .findings { padding-top: 25px; }
  ul { list-style: none; margin: 13px 0 0; padding: 0; }
  li { opacity: .12; min-height: 49px; padding: 9px 0; border-top: 1px solid rgba(58,53,42,.75); }
  li.visible { opacity: 1; }
  li span { display: block; font-size: 13px; color: #e6dcc8; }
  li small { display: block; margin-top: 3px; color: var(--muted); font: 10px ui-monospace, SFMono-Regular, Menlo, monospace; }
  .check { display: flex; justify-content: space-between; align-items: center; }
  .check span { font-size: 12px; }
  .check b { color: var(--green); }
  .check small { margin: 0; color: var(--green); }
  footer { justify-content: space-between; border-top: 1px solid var(--line); color: var(--muted); font-size: 11px; }
  footer code { padding: 10px 14px; border: 1px solid var(--line); border-radius: 8px; color: #dcd2be; font: 11px ui-monospace, SFMono-Regular, Menlo, monospace; }
  footer code b { color: var(--green); }
</style>
</head>
<body><div id="stage"></div></body>
</html>`;

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const page = await browser.newPage({
  viewport: { width: W, height: H },
  deviceScaleFactor: 1,
});
await page.setContent(pageHtml);

const buffers = [];
for (const state of timeline) {
  await page.locator("#stage").evaluate((element, html) => {
    element.innerHTML = html;
  }, frameMarkup(state));
  const png = await page.screenshot({ type: "png" });
  buffers.push(await sharp(png).removeAlpha().raw().toBuffer());
}
await browser.close();

await mkdir(dirname(out), { recursive: true });
await sharp(Buffer.concat(buffers), {
  raw: { width: W, height: H * buffers.length, channels: 3, pageHeight: H },
})
  .gif({ loop: 0, delay: timeline.map((frame) => frame.delay), colours: 128 })
  .toFile(out);

const runtime = timeline.reduce((sum, frame) => sum + frame.delay, 0);
const meta = await sharp(out, { animated: true }).metadata();
console.log(`wrote ${out}`);
console.log(`  ${meta.pages} frames, ${meta.width}x${meta.pageHeight}, ${(runtime / 1000).toFixed(1)}s`);
