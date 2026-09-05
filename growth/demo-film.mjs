// Deterministic ANSI replay in the real xterm.js renderer. This is a saved
// installed-skill example, not a screen recording or a claim about latency.
export const WIDTH = 1280;
export const HEIGHT = 720;
export const DURATION = 36000;
export const POSTER_TIME = 26000;
export const MCP_URL = "https://mcp.zero-slop.ai/mcp";

const INSTALL = "npx skills add manavmishra/ZeroSlop --global";
const INVOCATION = "/zero-slop";
const SHELL_TYPE = { start: 350, end: 2050, text: INSTALL };
const ASSISTANT_TYPE = { start: 4250, end: 5150, text: INVOCATION };
const OUTPUT_TIMES = [4000, 6000, 12000, 12200, 12800, 13400, 14000, 16400, 17200, 22000, 23000, 24000, 25200, 30000, 30600];

export const CAPTIONS = [
  "Zero Slop in your terminal.",
  "Shell",
  INSTALL,
  "Install once. Then restart your assistant.",
  "AI assistant",
  INVOCATION,
  "Paste your draft after /zero-slop.",
  "Zero Slop",
  "Writing score: 99.3/100 (lower is better) | 4 flagged phrases",
  "canned opener",
  "promotional verb",
  "unsupported hype",
  "promotional claim",
  "Edit",
  "Your assistant edits. Local tools compare source details.",
  "Source figure retained: 40%.",
  "Writing score: 9.5/100 (lower is better)",
  "Flagged phrases: 0",
  "Review the edit before you use it.",
  "Optional hosted MCP",
  MCP_URL,
  "Or try the free browser editor",
  "zero-slop.ai/try",
  "Reconstructed skill session. Timing edited for readability.",
];

const escapeHTML = (value) => String(value)
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const scriptJSON = (value) => JSON.stringify(value).replaceAll("<", "\\u003c");

// Called inside the isolated render document. The transcript is rebuilt from
// scratch at every requested timestamp, so a seek cannot inherit stale state.
function initialiseFilm(payload) {
  const { before, after, beforeScore, afterScore, flags, install, invocation } = payload;
  const COLS = 76;
  const ROWS = 14;
  const ESC = "\u001b[";
  const RESET = ESC + "0m";
  const INK = ESC + "38;2;18;16;12m";
  const MUTED = ESC + "38;2;104;100;94m";
  const RUST = ESC + "38;2;140;63;34m";
  const BOLD = ESC + "1m";
  const terminal = new Terminal({
    cols: COLS, rows: ROWS,
    fontFamily: '"SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace',
    fontSize: 24, lineHeight: 1.1, letterSpacing: 0,
    fontWeight: "400", fontWeightBold: "600",
    cursorBlink: false, cursorStyle: "bar", cursorInactiveStyle: "bar", cursorWidth: 2,
    allowTransparency: false, convertEol: false, disableStdin: true,
    scrollback: 100, smoothScrollDuration: 0,
    theme: {
      background: "#ffffff", foreground: "#12100c", cursor: "#8c3f22",
      cursorAccent: "#ffffff", selectionBackground: "#eae6e0",
      black: "#12100c", red: "#8c3f22", green: "#12100c", yellow: "#68645e",
      blue: "#12100c", magenta: "#8c3f22", cyan: "#68645e", white: "#ffffff",
      brightBlack: "#68645e", brightRed: "#8c3f22", brightGreen: "#12100c",
      brightYellow: "#68645e", brightBlue: "#12100c", brightMagenta: "#8c3f22",
      brightCyan: "#68645e", brightWhite: "#ffffff",
    },
  });
  terminal.open(document.querySelector("#terminal"));
  terminal.focus();
  window.filmTerminal = terminal;

  const wrap = (text, width = COLS - 4) => {
    const output = [];
    let line = "";
    for (const word of text.split(/\s+/)) {
      if (line && line.length + word.length + 1 > width) {
        output.push("  " + line);
        line = word;
      } else line += (line ? " " : "") + word;
    }
    if (line) output.push("  " + line);
    return output;
  };
  const type = (text, t, start, end) => text.slice(0,
    Math.max(0, Math.min(text.length, Math.floor((t - start) / (end - start) * text.length))));
  const label = (text) => BOLD + text + RESET;
  const tint = (text, color) => color + text + RESET;
  const colors = (line, active) => {
    for (const phrase of flags.slice(0, active)) {
      line = line.replace(phrase, RUST + phrase + RESET);
    }
    return line;
  };
  const reasons = ["canned opener", "promotional verb", "unsupported hype", "promotional claim"];

  function transcript(t) {
    const lines = [tint("$", RUST) + " " + type(install, t, 350, 2050)];
    if (t >= 4000) lines.push("", label("AI assistant"), "", tint("›", RUST) + " " + type(invocation, t, 4250, 5150));
    const activeFlags = [12200, 12800, 13400, 14000].filter((at) => t >= at).length;
    if (t >= 6000) lines.push("", ...wrap(before).map((line) => colors(line, activeFlags)));
    if (t >= 12000) lines.push("", label("Zero Slop"), tint(`Writing score: ${beforeScore}/100 (lower is better) | 4 flagged phrases`, MUTED));
    for (let i = 0; i < activeFlags; i += 1) {
      lines.push("  " + tint('"' + flags[i] + '"', RUST) + " ".repeat(Math.max(2, 21 - flags[i].length)) + tint(reasons[i], MUTED));
    }
    if (t >= 16400) lines.push("", label("Edit"));
    if (t >= 17200) lines.push(...wrap(after).map((line) => INK + line + RESET));
    if (t >= 22000) lines.push("", "Source figure retained: " + tint("40%.", RUST));
    if (t >= 23000) lines.push(tint(`Writing score: ${afterScore}/100 (lower is better)`, MUTED));
    if (t >= 24000) lines.push(tint("Flagged phrases: 0", MUTED));
    if (t >= 25200) lines.push("", tint("›", RUST) + " ");
    const cursor = t < 2050 || (t >= 4000 && t < 6000) || t >= 25200;
    return RESET + INK + lines.join("\r\n") + (cursor ? ESC + "?25h" : ESC + "?25l");
  }

  function inspect() {
    const buffer = terminal.buffer.active;
    const all = [];
    for (let i = 0; i < buffer.length; i += 1) all.push(buffer.getLine(i)?.translateToString(true) ?? "");
    return {
      cols: terminal.cols, rows: terminal.rows, cursorX: buffer.cursorX, cursorY: buffer.cursorY,
      baseY: buffer.baseY, viewportY: buffer.viewportY,
      visibleLines: all.slice(buffer.viewportY, buffer.viewportY + terminal.rows), allLines: all,
    };
  }
  window.filmInspection = inspect;

  let pending = Promise.resolve();
  const paint = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  const clamp = (x) => Math.max(0, Math.min(1, x));
  const ease = (x) => 1 - Math.pow(1 - clamp(x), 3);
  async function draw(time) {
    const t = Math.max(0, Math.min(35999, Number(time) || 0));
    terminal.reset();
    await new Promise((resolve) => terminal.write(transcript(t), resolve));
    terminal.scrollToBottom();
    terminal.refresh(0, terminal.rows - 1);
    const closing = ease((t - 30000) / 600);
    document.querySelector(".terminal-shell").style.transform = `translateY(${-28 * closing}px) scale(${1 - 0.17 * closing})`;
    document.querySelector(".closing").style.opacity = String(closing);
    document.querySelector(".closing").style.transform = `translateY(${10 * (1 - closing)}px)`;
    document.querySelector(".instruction").style.opacity = String(1 - closing);
    document.querySelector(".instruction").textContent = t < 4000
      ? "Install once. Then restart your assistant."
      : t < 12000 ? "Paste your draft after /zero-slop."
      : t < 22000 ? "Your assistant edits. Local tools compare source details."
      : "Review the edit before you use it.";
    document.querySelector(".session-label").textContent = t < 4000 ? "Shell" : "AI assistant";
    const underline = document.querySelector(".signature");
    const visible = inspect().visibleLines;
    const resultRow = visible.findIndex((line) => line.trim().startsWith(after.slice(0, 15)));
    const xtermRows = document.querySelector(".xterm-rows");
    const rowHeight = xtermRows ? xtermRows.getBoundingClientRect().height / ROWS / (1 - 0.17 * closing) : 31;
    underline.style.top = `${57 + (resultRow + 1) * rowHeight}px`;
    const stroke = ease((t - 17600) / 380);
    const fade = 1 - ease((t - 18700) / 400);
    underline.style.opacity = String(resultRow >= 0 && t >= 17600 && t < 19100 ? fade : 0);
    underline.style.transform = `rotate(-2deg) scaleX(${stroke})`;
    document.querySelector("#film").dataset.time = String(Math.round(t));
    await paint();
    window.filmState = inspect();
    return window.filmState;
  }
  window.renderFrame = (t) => {
    pending = pending.then(() => draw(t));
    return pending;
  };
  window.filmReady = document.fonts.ready.then(() => window.renderFrame(0));
}

export function filmHTML({ logo, before, after, beforeScore, afterScore, flags, xtermJS, xtermCSS }) {
  if (flags.length !== 4 || flags.some((flag) => !before.includes(flag))) throw new Error("Expected four measured source flags");
  if (!xtermJS || !xtermCSS) throw new Error("The real xterm.js renderer and stylesheet are required");
  if ([before, after, ...flags].some((text) => /[\u0000-\u001f\u007f]/.test(text))) throw new Error("Unexpected terminal control character in source");
  const css = `
    :root { color-scheme:light; --ink:#12100c; --muted:#68645e; --rust:#8c3f22; --line:#e5e1db; }
    * { box-sizing:border-box; }
    html,body { margin:0; width:1280px; height:720px; overflow:hidden; background:#fff; }
    body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; color:var(--ink); -webkit-font-smoothing:antialiased; }
    #film { position:relative; width:1280px; height:720px; background:#fff; overflow:hidden; }
    .brand { position:absolute; top:25px; left:52px; height:70px; display:flex; align-items:center; gap:14px; }
    .brand svg { width:64px; height:64px; display:block; }
    h1 { margin:0; font-size:32px; line-height:1.15; font-weight:620; letter-spacing:-1.15px; }
    .terminal-shell { position:absolute; left:52px; top:119px; width:1176px; height:514px; border:1px solid var(--line); border-radius:12px; background:#fff; box-shadow:0 8px 24px rgba(104,100,94,.055); transform-origin:50% 0; overflow:hidden; }
    .terminal-bar { height:43px; border-bottom:1px solid var(--line); background:#faf9f7; display:flex; align-items:center; justify-content:center; position:relative; }
    .window-controls { position:absolute; left:20px; display:flex; align-items:center; gap:8px; }
    .window-controls i { width:8px; height:8px; border:1px solid #b8b3ab; border-radius:50%; }
    .session-label { font-size:15px; color:var(--muted); line-height:1; }
    #terminal { position:absolute; left:27px; top:57px; right:20px; height:438px; background:#fff; }
    .xterm { background:#fff!important; }
    .xterm-viewport { scrollbar-width:none; }
    .xterm-viewport::-webkit-scrollbar { display:none; }
    .xterm .xterm-scrollable-element > .scrollbar { opacity:0!important; }
    .signature { position:absolute; left:54px; width:104px; height:3px; border-radius:2px; background:var(--rust); transform-origin:0 50%; pointer-events:none; opacity:0; }
    .instruction { position:absolute; left:57px; top:652px; margin:0; font-size:20px; line-height:1.25; color:var(--muted); letter-spacing:-.2px; }
    .closing { position:absolute; left:104px; right:104px; top:545px; display:grid; grid-template-columns:1.7fr 1fr; gap:38px; opacity:0; }
    .closing p { margin:0 0 12px; color:var(--muted); font-size:20px; line-height:1.2; }
    .closing a { color:var(--rust); text-decoration:none; font-size:32px; font-weight:520; letter-spacing:-.85px; white-space:nowrap; }
    .closing .secondary { padding-left:31px; border-left:1px solid var(--line); }
    .closing .secondary a { color:var(--ink); font-size:28px; letter-spacing:-.5px; }
    footer { position:absolute; left:57px; right:57px; bottom:16px; display:flex; justify-content:space-between; font-size:14px; color:var(--muted); line-height:1.25; }
    @media (prefers-reduced-motion:reduce) { * { animation:none!important; transition:none!important; } }
  `;
  const payload = { before, after, beforeScore, afterScore, flags, install: INSTALL, invocation: INVOCATION };
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Zero Slop: terminal skill demo</title>
<style>${xtermCSS}</style><style>${css}</style></head>
<body><main id="film" aria-label="Reconstructed Zero Slop skill session: install in a shell, invoke in your AI assistant, and review a source-checked edit.">
<header class="brand">${logo}<h1>Zero Slop in your terminal.</h1></header>
<section class="terminal-shell" aria-label="Zero Slop terminal session">
  <div class="terminal-bar"><span class="window-controls" aria-hidden="true"><i></i><i></i><i></i></span><span class="session-label">Shell</span></div>
  <div id="terminal"></div><i class="signature" aria-hidden="true"></i>
</section>
<p class="instruction">Install once. Then restart your assistant.</p>
<section class="closing" aria-label="Optional ways to use Zero Slop">
  <div><p>Optional hosted MCP</p><a href="${escapeHTML(MCP_URL)}">${escapeHTML(MCP_URL)}</a></div>
  <div class="secondary"><p>Or try the free browser editor</p><a href="https://zero-slop.ai/try/">zero-slop.ai/try</a></div>
</section>
<footer><span>Reconstructed skill session. Timing edited for readability.</span><span>zero-slop.ai</span></footer>
</main><script>${xtermJS.replaceAll("</script", "<\\/script")}</script>
<script>(${initialiseFilm.toString()})(${scriptJSON(payload)});</script></body></html>`;
}

// Dense frames only while a command is typed or a motivated state gesture is
// moving. All reading holds are a single frame with its own duration.
export function timeline(fps = 30) {
  if (!(fps > 0 && fps <= 120)) throw new Error("fps must be between 0 and 120");
  const times = new Set([0, ...OUTPUT_TIMES]);
  for (const typing of [SHELL_TYPE, ASSISTANT_TYPE]) {
    for (let n = 0; n <= typing.text.length; n += 1) {
      times.add(Math.round(typing.start + (typing.end - typing.start) * n / typing.text.length));
    }
  }
  for (const [start, end] of [[17600, 17980], [18700, 19100], [30000, 30600]]) {
    for (let t = start; t < end; t += 1000 / fps) times.add(Math.round(t));
    times.add(end);
  }
  const ordered = [...times].filter((t) => t >= 0 && t < DURATION).sort((a, b) => a - b);
  return ordered.map((t, i) => ({ t, durationMs: (ordered[i + 1] ?? DURATION) - t }));
}
