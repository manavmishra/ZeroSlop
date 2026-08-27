#!/usr/bin/env node
// Render the sharing card in GitHub (1280x640) or Open Graph (1200x630) form.
// GitHub exposes no API for repo social previews, so uploading that card remains
// a manual step in Settings -> General -> Social preview.
//
// Usage: node growth/make-social-preview.mjs [outfile] [width] [height]

import { chromium } from "../website/node_modules/playwright-core/index.mjs";
import { writeFile } from "node:fs/promises";

const out = process.argv[2] ?? "assets/social-preview.png";
const width = Number(process.argv[3] ?? 1280);
const height = Number(process.argv[4] ?? 640);
const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

if (!Number.isFinite(width) || !Number.isFinite(height) || width < 800 || height < 400) {
  throw new Error("width and height must be reasonable positive numbers");
}

const html = `<!doctype html>
<html><head><meta charset="utf-8"><style>
  * { box-sizing:border-box; }
  body { margin:0; width:${width}px; height:${height}px; padding:52px 58px 44px;
    overflow:hidden; background:#f6f5ef; color:#151a17;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
  header, footer { display:flex; align-items:center; justify-content:space-between; }
  .brand { display:flex; align-items:center; gap:12px; color:#17694f; font-size:18px;
    font-weight:750; letter-spacing:.14em; text-transform:uppercase; }
  .brand i { width:12px; height:12px; border-radius:3px; background:#17694f; }
  .mono { color:#6b756f; font:500 14px ui-monospace,SFMono-Regular,Menlo,monospace; }
  main { height:430px; display:grid; grid-template-columns:.82fr 1.18fr; gap:54px;
    align-items:center; }
  .kicker { margin-bottom:17px; color:#9a5c19; font:700 13px ui-monospace,
    SFMono-Regular,Menlo,monospace; letter-spacing:.13em; text-transform:uppercase; }
  h1 { margin:0; font-size:70px; line-height:.98; letter-spacing:-.055em; }
  h1 span { color:#17694f; }
  .lede { max-width:440px; margin:24px 0 0; color:#58635d; font-size:19px;
    line-height:1.48; }
  .panel { padding:24px; border:1px solid #cdd5cf; border-radius:22px;
    background:#fff; box-shadow:0 22px 55px rgba(26,44,34,.09); }
  .panel-head { display:flex; justify-content:space-between; margin:0 2px 18px;
    color:#5b6861; font:650 12px ui-monospace,SFMono-Regular,Menlo,monospace;
    letter-spacing:.08em; text-transform:uppercase; }
  .roles { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .role { min-height:105px; padding:17px 18px; border:1px solid #d9dfda;
    border-radius:14px; background:#f8faf8; }
  .role.read { background:#f8f3e9; border-color:#d6b98e; }
  .role.fresh { background:#f2eef6; border-color:#a991bc; }
  .role b { display:block; margin-bottom:8px; font-size:18px; }
  .role span { color:#68736d; font-size:13px; line-height:1.35; }
  .loop { margin-top:13px; padding:11px 14px; border-radius:11px; color:#81501b;
    background:#fbf4e9; font:600 12px ui-monospace,SFMono-Regular,Menlo,monospace;
    text-align:center; }
  footer { padding-top:19px; border-top:1px solid #d9ded9; }
  footer strong { color:#1f2c25; font-weight:700; }
</style></head><body>
  <header>
    <div class="brand"><i></i>Zero Slop</div>
    <div class="mono">zero-slop.ai · v2.6.0</div>
  </header>
  <main>
    <section>
      <div class="kicker">AI writing editor</div>
      <h1>Less slop.<br><span>More pop.</span></h1>
      <p class="lede">Eight focused roles take an AI-assisted draft from rewrite to polished, source-checked copy.</p>
    </section>
    <section class="panel">
      <div class="panel-head"><span>One editorial pipeline</span><span>Selected roles</span></div>
      <div class="roles">
        <div class="role"><b>3 · Rewriter</b><span>Rebuilds order, rhythm, and tone.</span></div>
        <div class="role"><b>5 · Copy desk</b><span>Corrects grammar, usage, and consistency.</span></div>
        <div class="role read"><b>6 · Read aloud</b><span>Fixes stumbles, transitions, and repetition.</span></div>
        <div class="role fresh"><b>8 · Fresh eyes</b><span>Reads as a first-time reader and approves unchanged.</span></div>
      </div>
      <div class="loop">ANY FINAL POLISH → COPY EDIT → READ ALOUD → VERIFY → FRESH EYES</div>
    </section>
  </main>
  <footer>
    <div class="mono"><strong>Agent Skill</strong> · MIT · local checks · private learning</div>
    <div class="mono">npx skills add manavmishra/ZeroSlop</div>
  </footer>
</body></html>`;

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
try {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: "load" });
  const jpeg = /\.jpe?g$/i.test(out);
  const buffer = await page.screenshot(jpeg
    ? { type: "jpeg", quality: 90 }
    : { type: "png" });
  await writeFile(out, buffer);
  console.log(`wrote ${out} (${(buffer.length / 1024).toFixed(0)} KB, ${width}x${height})`);
} finally {
  await browser.close();
}
