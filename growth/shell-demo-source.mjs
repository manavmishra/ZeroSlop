#!/usr/bin/env node
// Renders assets/zero-slop-demo.gif, the terminal screencast at the top of the
// README.
//
// Usage: node scripts/make-readme-gif.mjs [outfile]
//
// No new dependencies. Playwright's Chromium paints the frames and sharp
// encodes them, both of which the repository already has. Playwright does ship
// an ffmpeg, but it is a stripped build with only PNG and VP8 encoders and no
// GIF muxer, so it cannot do this job; sharp's libvips is built with cgif and
// can, given a raw buffer of frames stacked vertically and a raw.pageHeight.
//
// The scorer output in the script below is real. It is what
// `scripts/slopscore.py --explain` prints for the draft shown, and the same
// numbers appear in the README next to the same paragraph, and they must stay
// equal to it: the README's rewrite was tightened after this file first
// carried a different one, and the screencast went stale the same day.
// Re-run the scorer
// before editing any figure here: a screencast that overstates the meter would
// be the one piece of slop in the repository.

import { chromium } from "playwright-core";
import sharp from "sharp";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const out = resolve(process.argv[2] ?? "assets/zero-slop-demo.gif");
const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const W = 900;
const H = 580;

// The dark surface scale and accents the website uses, so the GIF and the site
// look like the same product.
const C = {
  bg: "#1b1a18",
  chrome: "#242320",
  line: "#393835",
  ink: "#ececea",
  muted: "#c8c7c4",
  dim: "#8e8d88",
  amber: "#f2c14e",
  green: "#5fc493",
  rust: "#d3714a",
};

const PROMPT = `<span style="color:${C.green}">$</span> `;

// One entry per line of the session. `type` lines are revealed a few characters
// at a time; everything else appears whole, because a machine does not type its
// own output.
const SCRIPT = [
  { kind: "type", text: "npx zero-slop install", hold: 6 },
  { kind: "out", html: `<span style="color:${C.dim}">installed to ~/.claude/skills/zero-slop</span>`, hold: 5 },
  { kind: "gap" },
  { kind: "type", text: "zero-slop score post.md", hold: 3 },
  { kind: "out", html: `<span style="color:${C.ink}">Writing score: </span><span style="color:${C.rust};font-weight:600">100.0/100</span><span style="color:${C.dim}">  [major rewrite]</span>`, hold: 4 },
  { kind: "out", html: `<span style="color:${C.muted}">  Flagged phrases : 11 across 83 words</span>`, hold: 2 },
  { kind: "out", html: `<span style="color:${C.muted}">  Sentence variety: too even</span>`, hold: 4 },
  { kind: "gap" },
  { kind: "out", html: `<span style="color:${C.amber}">  "In today's fast-paced"</span><span style="color:${C.dim}">   manufactured stakes</span>`, hold: 2 },
  { kind: "out", html: `<span style="color:${C.amber}">  "We're thrilled to"</span><span style="color:${C.dim}">       canned LinkedIn phrase</span>`, hold: 2 },
  { kind: "out", html: `<span style="color:${C.amber}">  "It's not X, it's Y"</span><span style="color:${C.dim}">      two-part contrast as formula</span>`, hold: 2 },
  { kind: "out", html: `<span style="color:${C.amber}">  'cutting-edge'</span><span style="color:${C.dim}">            promotional language</span>`, hold: 2 },
  { kind: "out", html: `<span style="color:${C.amber}">  'leveraged'</span><span style="color:${C.dim}">               buzzword used as promotion</span>`, hold: 6 },
  { kind: "gap" },
  { kind: "type", text: "/zero-slop post.md", hold: 3 },
  { kind: "out", html: `<span style="color:${C.dim}">  rewriting, then checking names, numbers, quotes, links</span>`, hold: 7 },
  { kind: "out", html: `<span style="color:${C.green}">  fact gate: 40% held</span>`, hold: 5 },
  { kind: "gap" },
  { kind: "out", html: `<span style="color:${C.ink}">Writing score: </span><span style="color:${C.green};font-weight:600">9.5/100</span><span style="color:${C.dim}">  [clear]</span>`, hold: 4 },
  { kind: "out", html: `<span style="color:${C.muted}">  Flagged phrases : 0 across 10 words</span>`, hold: 26 },
];

const CHARS_PER_FRAME = 3;
const TICK_MS = 150;

/**
 * One entry per *distinct* state, carrying its own delay.
 *
 * Repeating an identical frame to hold it on screen does not work: libvips
 * collapses consecutive duplicates, which leaves the delay array longer than
 * the frame list and throws the timing out. A hold is a longer delay on one
 * frame, not the same frame many times.
 */
function buildFrames() {
  const frames = [];
  const done = [];
  const add = (extra, ticks) =>
    frames.push({ html: [...done, ...(extra ? [extra] : [])].join("\n"), delay: ticks * TICK_MS });

  for (const step of SCRIPT) {
    if (step.kind === "gap") {
      done.push("&nbsp;");
      continue;
    }
    if (step.kind === "type") {
      for (let n = CHARS_PER_FRAME; n < step.text.length; n += CHARS_PER_FRAME) {
        add(`${PROMPT}${step.text.slice(0, n)}<i class="c"></i>`, 1);
      }
      done.push(`${PROMPT}${step.text}`);
      add(null, step.hold);
      continue;
    }
    done.push(step.html);
    add(null, step.hold);
  }
  return frames;
}

const page = `<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{width:${W}px;height:${H}px;background:${C.bg};font-family:'IBM Plex Mono',monospace;
       overflow:hidden;-webkit-font-smoothing:antialiased}
  .bar{height:38px;background:${C.chrome};border-bottom:1px solid ${C.line};
       display:flex;align-items:center;gap:8px;padding:0 14px}
  .dot{width:11px;height:11px;border-radius:50%}
  .title{margin-left:10px;color:${C.dim};font-size:12.5px;letter-spacing:.04em}
  .body{padding:18px 22px;font-size:15px;line-height:1.62;color:${C.ink};white-space:pre}
  .c{display:inline-block;width:8px;height:16px;background:${C.amber};
     vertical-align:-3px;margin-left:1px}
</style></head><body>
  <div class="bar">
    <span class="dot" style="background:#5c5b57"></span>
    <span class="dot" style="background:#5c5b57"></span>
    <span class="dot" style="background:#5c5b57"></span>
    <span class="title">zero-slop</span>
  </div>
  <div class="body" id="t"></div>
</body></html>`;

const frames = buildFrames();
const runtime = frames.reduce((n, f) => n + f.delay, 0);
console.log(`frames: ${frames.length}  (~${(runtime / 1000).toFixed(1)}s)`);

const browser = await chromium.launch({ executablePath: chromePath });
const tab = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await tab.setContent(page, { waitUntil: "networkidle" });
await tab.evaluate(() => document.fonts.ready);

const raw = [];
for (const frame of frames) {
  await tab.evaluate((html) => { document.getElementById("t").innerHTML = html; }, frame.html);
  const shot = await tab.screenshot({ type: "png" });
  raw.push(await sharp(shot).ensureAlpha().raw().toBuffer());
}
await browser.close();

await mkdir(dirname(out), { recursive: true });
await sharp(Buffer.concat(raw), {
  raw: { width: W, height: H * raw.length, channels: 4, pageHeight: H },
})
  .gif({ loop: 0, delay: frames.map((f) => f.delay) })
  .toFile(out);

const meta = await sharp(out, { animated: true }).metadata();
console.log(`wrote ${out}`);
console.log(`  ${meta.pages} frames, ${meta.width}x${meta.pageHeight}, ${(runtime / 1000).toFixed(1)}s`);
if (meta.pages !== frames.length) {
  console.warn(`  warning: encoder kept ${meta.pages} of ${frames.length} frames; delays may be out of step`);
}
