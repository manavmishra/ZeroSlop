// A typeset replay of an actual installed-skill example, not a product UI.
// No external assets, runtime dependencies, sound, or implied latency claim.
export const WIDTH = 1280;
export const HEIGHT = 720;
export const DURATION = 36000;
export const POSTER_TIME = 26700;

export const CAPTIONS = [
  "Clean up AI writing.",
  "Install once, in your terminal.",
  "npx skills add manavmishra/ZeroSlop --global",
  "Use it in your AI assistant.",
  "/zero-slop",
  "Find the stock phrases.",
  "Four stock phrases flagged.",
  "Read the edit.",
  "Your assistant rewrites. Zero Slop checks the source.",
  "40% setup-time reduction retained.",
  "Writing score (lower is better)",
  "Before and after.",
  "The draft",
  "The edit",
  "Try it on your next draft.",
  "/zero-slop [your draft]",
  "Try it free in your browser.",
  "zero-slop.ai/try",
  "Free. No account needed.",
  "Or connect the hosted MCP.",
  "zero-slop.ai/#mcp",
  "Agent Skill example. Sequence edited for readability.",
];

const escapeHTML = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

function markSource(source, flags) {
  const matches = [];
  for (const [index, phrase] of flags.entries()) {
    const start = source.indexOf(phrase);
    if (start < 0) throw new Error(`Flag absent from source: ${phrase}`);
    matches.push({ start, end: start + phrase.length, index });
  }
  matches.sort((a, b) => a.start - b.start);
  let cursor = 0;
  let output = "";
  for (const match of matches) {
    if (match.start < cursor) throw new Error("Overlapping source flags");
    output += escapeHTML(source.slice(cursor, match.start));
    output += `<mark data-flag="${match.index}">${escapeHTML(source.slice(match.start, match.end))}</mark>`;
    cursor = match.end;
  }
  output += escapeHTML(source.slice(cursor));
  return output.replaceAll("40%", '<strong class="fact-number">40%</strong>');
}

function frame(t) {
  t = Math.max(0, Math.min(35999, Number(t) || 0));
  const unit = (x) => Math.max(0, Math.min(1, x));
  const ease = (x) => 1 - Math.pow(1 - unit(x), 3);
  const ramp = (start, end) => ease((t - start) / (end - start));
  const state = (selector, opacity, y = 0) => {
    for (const element of document.querySelectorAll(selector)) {
      element.style.opacity = String(opacity);
      element.style.transform = `translateY(${y}px)`;
      element.setAttribute("aria-hidden", opacity === 0 ? "true" : "false");
    }
  };
  const scene = (selector, start, entered, leaving, end) => {
    const incoming = start === 0 ? 1 : ramp(start, entered);
    const outgoing = end === Infinity ? 0 : ramp(leaving, end);
    state(selector, incoming * (1 - outgoing), 14 * (1 - incoming) - 8 * outgoing);
  };

  // A scene has left before its successor enters. No double-exposed type.
  scene(".install", 0, 0, 4800, 5000);
  scene(".ask", 5000, 5320, 16420, 16600);
  scene(".result", 16920, 17240, 23760, 24000);
  scene(".comparison", 24000, 24320, 29260, 29500);
  scene(".closing", 29500, 29860, Infinity, Infinity);

  state(".ask-title", 1 - ramp(12840, 13000));
  state(".inspect-title", ramp(13000, 13200));
  state(".flag-report", ramp(14360, 14600));
  state(".source-score", ramp(14360, 14600));
  const flagTimes = [13320, 13640, 13960, 14280];
  for (const mark of document.querySelectorAll(".source mark")) {
    mark.classList.toggle("flagged", t >= flagTimes[Number(mark.dataset.flag)]);
  }

  // The existing logo's angle and rust bar are the single signature gesture.
  const cut = document.querySelector(".signature-cut");
  const draw = ramp(16520, 16820);
  const leave = ramp(16820, 17140);
  cut.style.opacity = String(t >= 16520 && t < 17140 ? 1 - leave : 0);
  cut.style.transform = `translate(${leave * 1460}px,${-leave * 205}px) rotate(-8deg) scaleX(${draw})`;

  const proofIn = ramp(19200, 19520);
  state(".result-proof", proofIn, 7 * (1 - proofIn));
  document.querySelector("#film").dataset.time = String(Math.round(t));
}

export function filmHTML({ logo, before, after, beforeScore, afterScore, flags }) {
  if (flags.length !== 4) throw new Error("This storyboard requires four measured source flags");
  const source = markSource(before, flags);
  const edited = escapeHTML(after).replaceAll("40%", '<strong class="fact-number">40%</strong>');
  const scoreBefore = escapeHTML(beforeScore);
  const scoreAfter = escapeHTML(afterScore);
  const css = `
    :root { color-scheme: light; --ink:#12100c; --rust:#b0502c; --muted:#68645e; --line:#e5e1db; }
    * { box-sizing:border-box; }
    html,body { margin:0; width:1280px; height:720px; overflow:hidden; background:#fff; }
    body { color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; -webkit-font-smoothing:antialiased; }
    #film { position:relative; width:1280px; height:720px; overflow:hidden; background:#fff; }
    p,h1,h2 { margin:0; }
    .brand { position:absolute; top:32px; left:64px; display:flex; align-items:center; gap:12px; height:58px; }
    .brand svg { display:block; width:58px; height:58px; }
    .brand span { font-size:29px; font-weight:720; letter-spacing:-1.15px; }
    .scene { position:absolute; left:72px; top:146px; width:1136px; height:478px; opacity:0; }
    .scene h1 { font-size:54px; line-height:1.08; letter-spacing:-2.2px; font-weight:620; }
    .install h1 { font-size:76px; line-height:1.05; letter-spacing:-3.8px; max-width:1040px; }
    .install .instruction { margin-top:54px; color:var(--muted); font-size:27px; letter-spacing:-.5px; }
    code { font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace; }
    .install code { display:block; margin-top:21px; padding:29px 28px; border:1px solid var(--line); border-left:4px solid var(--rust); border-radius:4px; font-size:32px; line-height:1.3; letter-spacing:-.85px; white-space:nowrap; }
    .ask h1 { position:absolute; top:0; left:0; }
    .prompt { position:absolute; top:102px; left:0; width:1108px; border-left:3px solid var(--line); padding-left:28px; }
    .invocation { display:block; margin-bottom:25px; color:var(--rust); font-size:29px; line-height:1.3; letter-spacing:-.5px; }
    .source { font-size:36px; line-height:1.4; letter-spacing:-1px; font-weight:430; }
    mark { color:inherit; background:transparent; box-decoration-break:clone; -webkit-box-decoration-break:clone; border-radius:2px; }
    mark.flagged,.original mark { background:#f8e9e2; color:#823c22; box-shadow:0 2px 0 var(--rust); }
    .fact-number { font-weight:inherit; color:var(--rust); }
    .flag-report { position:absolute; left:0; bottom:10px; font-size:22px; color:var(--rust); }
    .source-score { position:absolute; right:0; bottom:10px; display:flex; align-items:baseline; gap:17px; font-size:19px; color:var(--muted); }
    .source-score b { font-weight:600; font-size:30px; color:var(--ink); font-variant-numeric:tabular-nums; letter-spacing:-.8px; }
    .edited { margin-top:53px; max-width:1080px; font-size:58px; line-height:1.21; letter-spacing:-2.2px; font-weight:530; }
    .result .explanation { position:absolute; bottom:0; left:0; font-size:22px; color:var(--muted); }
    .result-proof { position:absolute; left:0; right:0; bottom:69px; display:flex; align-items:center; justify-content:space-between; gap:20px; padding-top:19px; border-top:1px solid var(--line); }
    .preserved { color:var(--rust); font-size:24px; letter-spacing:-.4px; }
    .result-score { color:var(--muted); font-size:19px; }
    .result-score b { color:var(--ink); font-size:31px; font-weight:600; letter-spacing:-1px; margin-left:15px; font-variant-numeric:tabular-nums; }
    .comparison h1 { font-size:48px; }
    .columns { display:grid; grid-template-columns:1fr 1fr; gap:46px; margin-top:34px; height:354px; }
    .column { position:relative; min-width:0; }
    .column + .column { border-left:1px solid var(--line); padding-left:39px; }
    .column h2 { margin-bottom:21px; font-size:19px; color:var(--muted); font-weight:550; letter-spacing:-.2px; }
    .original { font-size:27px; line-height:1.43; letter-spacing:-.5px; }
    .rewritten { font-size:38px; line-height:1.3; letter-spacing:-1.1px; font-weight:500; }
    .comparison-score { position:absolute; bottom:0; font-size:17px; color:var(--muted); }
    .comparison-score b { display:inline-block; margin-left:12px; color:var(--ink); font-size:28px; font-weight:600; letter-spacing:-.8px; font-variant-numeric:tabular-nums; }
    .comparison .preserved { position:absolute; left:0; bottom:-4px; font-size:21px; }
    .closing h1 { font-size:68px; letter-spacing:-3px; }
    .next { margin-top:32px; font-size:33px; color:var(--rust); letter-spacing:-1px; line-height:1.4; }
    .end-links { display:grid; grid-template-columns:1.13fr 1fr; gap:46px; margin-top:52px; padding-top:29px; border-top:1px solid var(--line); }
    .end-links p { font-size:23px; color:var(--muted); letter-spacing:-.3px; }
    .end-links a { display:block; margin-top:15px; font-size:37px; letter-spacing:-1.25px; line-height:1.2; color:var(--ink); text-decoration:none; }
    .end-links .secondary { border-left:1px solid var(--line); padding-left:38px; }
    .end-links .secondary p { font-size:21px; }
    .end-links .secondary a { margin-top:18px; font-size:31px; color:var(--rust); letter-spacing:-.8px; }
    .end-links .free { margin-top:16px; font-size:19px; }
    .signature-cut { position:absolute; left:-80px; top:425px; width:1400px; height:15px; border-radius:10px; background:var(--rust); transform-origin:left center; opacity:0; }
    footer { position:absolute; left:72px; right:72px; bottom:27px; display:flex; justify-content:space-between; gap:24px; border-top:1px solid var(--line); padding-top:18px; font-size:15px; line-height:1.3; color:var(--muted); }
    footer .domain { color:var(--ink); font-size:17px; letter-spacing:-.15px; }
    @media (prefers-reduced-motion:reduce) { * { animation:none!important; transition:none!important; } }
  `;
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Zero Slop: installed skill demo</title><style>${css}</style></head>
<body><main id="film" aria-label="Zero Slop installed skill example: install, ask your assistant, review the edit, and compare the source.">
  <header class="brand">${logo}<span>Zero Slop</span></header>
  <section class="scene install">
    <h1>Clean up AI writing.</h1>
    <p class="instruction">Install once, in your terminal.</p>
    <code>npx skills add manavmishra/ZeroSlop --global</code>
  </section>
  <section class="scene ask">
    <h1 class="ask-title">Use it in your AI assistant.</h1>
    <h1 class="inspect-title">Find the stock phrases.</h1>
    <div class="prompt"><code class="invocation">/zero-slop</code><p class="source">${source}</p></div>
    <p class="flag-report">Four stock phrases flagged.</p>
    <p class="source-score"><span>Writing score (lower is better)</span><b>${scoreBefore}</b></p>
  </section>
  <section class="scene result">
    <h1>Read the edit.</h1>
    <p class="edited">${edited}</p>
    <div class="result-proof"><p class="preserved">40% setup-time reduction retained.</p><p class="result-score">Writing score (lower is better)<b>${scoreAfter}</b></p></div>
    <p class="explanation">Your assistant rewrites. Zero Slop checks the source.</p>
  </section>
  <section class="scene comparison">
    <h1>Before and after.</h1>
    <div class="columns">
      <div class="column"><h2>The draft</h2><p class="original">${source}</p><p class="comparison-score">Writing score (lower is better)<b>${scoreBefore}</b></p></div>
      <div class="column"><h2>The edit</h2><p class="rewritten">${edited}</p><p class="comparison-score">Writing score (lower is better)<b>${scoreAfter}</b></p></div>
    </div>
    <p class="preserved">40% setup-time reduction retained.</p>
  </section>
  <section class="scene closing">
    <h1>Try it on your next draft.</h1>
    <p class="next"><code>/zero-slop [your draft]</code></p>
    <div class="end-links">
      <div><p>Try it free in your browser.</p><a href="https://zero-slop.ai/try/">zero-slop.ai/try</a><p class="free">Free. No account needed.</p></div>
      <div class="secondary"><p>Or connect the hosted MCP.</p><a href="https://zero-slop.ai/#mcp">zero-slop.ai/#mcp</a></div>
    </div>
  </section>
  <i class="signature-cut" aria-hidden="true"></i>
  <footer><span>Agent Skill example. Sequence edited for readability.</span><span class="domain">zero-slop.ai</span></footer>
</main><script>const renderFrame = ${frame.toString()}; window.renderFrame = renderFrame; renderFrame(matchMedia('(prefers-reduced-motion: reduce)').matches ? ${POSTER_TIME} : 0);</script></body></html>`;
}

export function timeline(fps = 30) {
  if (!Number.isFinite(fps) || fps < 1 || fps > 120) throw new Error("fps must be 1–120");
  const points = new Set([0, 4800, 5000, 5320, 12840, 13000, 13200, 13320, 13640, 13960, 14280, 14360, 14600, 16420, 16520, 16600, 16820, 16920, 17140, 17240, 19200, 19520, 23760, 24000, 24320, 29260, 29500, 29860, DURATION]);
  const transitions = [[4800, 5320], [12840, 13200], [14360, 14600], [16420, 17240], [19200, 19520], [23760, 24320], [29260, 29860]];
  for (const [start, end] of transitions) {
    for (let tick = 0; start + tick * 1000 / fps < end; tick++) {
      points.add(Math.round(start + tick * 1000 / fps));
    }
  }
  const times = [...points].sort((a, b) => a - b);
  return times.slice(0, -1).map((t, index) => ({ t, durationMs: times[index + 1] - t }));
}
