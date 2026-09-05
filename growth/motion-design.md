# Zero Slop product demo

A silent, 36-second terminal demo of the installed Agent Skill. It shows the
installation command, an assistant request with a complete draft, the edit, and
the local checks. xterm.js renders the character grid, ANSI styling, cursor and
scrollback. The transcript reconstructs the saved launch-post example; it is
not a screen recording or a latency measurement. Different host models can
return different edits.

This returns to the shell direction in commit `91ee2fc1`, with larger type,
the current example's measurements, and a clear distinction between the shell
and the AI assistant. The logo and white background remain unchanged.

## The story

| Time | Viewer sees |
|---|---|
| 0-4 s | The installation command is typed at the shell prompt |
| 4-6 s | The context changes to the AI assistant; `/zero-slop` is entered |
| 6-12 s | The complete source arrives as a paste and stays readable |
| 12-16.4 s | Four actual phrase flags appear as whole output lines |
| 16.4-22 s | The edit arrives; the rust signature briefly underlines it |
| 22-30 s | Source-detail and writing checks finish beneath the full edit |
| 30-36 s | The session recedes to reveal the exact MCP endpoint and browser option |

The original's 40% claim is a sample claim, not a Zero Slop performance result.
The scorer is rerun during rendering: 99.3 becomes 9.5, with four flagged phrases
becoming zero. The source check is also rerun. Its result concerns tracked
details; it does not establish that the original claim is true.

`growth/demo-evidence.json` records exact texts, source hashes, and full tool
output. It also identifies the terminal renderer and canonical MCP URL.
`growth/demo-film.mjs` owns the composition and timing. Only user commands are
typed character by character. Machine output arrives in complete lines; holds
leave time to read. No decorative spinner, fabricated processing time, or
eight-green-check animation implies independent reviews.

## MCP connection

The ending displays **`https://mcp.zero-slop.ai/mcp`**. Live read-only checks on
September 5, 2026 returned HTTP 200 for MCP initialization and `tools/list`;
the server identified itself as `zero-slop` 2.8.10 and listed `deslop`.
No tool was executed and no draft was sent during that check.

`https://zero-slop.ai/#mcp` is a setup guide, not the endpoint. Build and CI
checks compare the film's URL with `server.json` and require the player to
display the endpoint separately from its setup-guide link.

## Research behind the treatment

[Charm VHS](https://github.com/charmbracelet/vhs) makes commands, typing,
pauses, geometry and exports reproducible. [asciinema's player options](https://docs.asciinema.org/manual/player/options/)
recommend matching the recording's terminal dimensions and trimming idle gaps
instead of accelerating the whole session. Those practices informed the fixed
76-column grid, quick input and generous reading holds.

[xterm.js](https://xtermjs.org/docs/api/terminal/interfaces/iterminaloptions/)
supplies actual terminal layout and cursor behavior. Its opaque rendering keeps
the capture simple. The white shell uses 24px monospace text, a quiet title bar
and one rust accent. [Gum](https://github.com/charmbracelet/gum) and
[Lazygit](https://github.com/jesseduffield/lazygit) demonstrate specific terminal
jobs near the beginning of their READMEs; this film likewise completes one job.
These are observed documentation patterns, not evidence of a causal conversion lift.

## Deliverables

| File in `assets/` | Purpose |
|---|---|
| `zero-slop-demo.mp4` | 1920 × 1080, 30 fps H.264 film, silent, fast-start |
| `zero-slop-demo.webp` | 960 × 540 inline GitHub animation |
| `zero-slop-demo.gif` | Compatible inline fallback, existing URL preserved |
| `zero-slop-demo-poster.png` | 1280 × 720 result-and-checks still for reduced motion |
| `zero-slop-demo.html` | Native video player with controls and a text transcript |
| `logo/logo-300.png` | Existing 300 × 300 logo on white |
| `logo/logo-mark-300.png` | Existing 300 × 300 transparent logo |

The README's picture selects the still for reduced-motion preferences, then
WebP, then GIF. Only width is specified: GitHub's maximum-width styling would
distort a fixed-height image. The MP4 player never autoplays and exposes native
pause, seek, and replay controls. Its transcript also explains the source check.

## Rebuild

Build-time dependencies are Node.js, Chrome, `playwright-core`, `sharp`, and `@xterm/xterm` 6.0.0.
They add nothing to the published skill. `CHROME_PATH` and `NODE_PATH` can
point to existing build tools. MP4 encoding uses macOS AVFoundation through
Swift and requires Apple's command-line tools; no codec package is installed.

```sh
# Keep the terminal renderer outside the skill's dependency-free runtime.
npm install --prefix /tmp/zero-slop-media-deps @xterm/xterm@6.0.0 --ignore-scripts
ZERO_SLOP_MEDIA_DEPS=/tmp/zero-slop-media-deps \
  node scripts/make-readme-gif.mjs --frames /tmp/zero-slop-film-frames
swift -module-cache-path /tmp/zero-slop-swift-cache growth/encode-demo.swift \
  --manifest /tmp/zero-slop-film-frames/manifest.json \
  --output /tmp/zero-slop-demo-new.mp4 --width 1920 --height 1080 --fps 30
```

The encoder refuses to overwrite an existing output. Inspect the new MP4 before
replacing `assets/zero-slop-demo.mp4`. Use `--preview` with the Node command to
render key scenes before the complete export. PNG frames are 1080p; manifest
durations let readable holds reuse a frame at 30 fps.

```sh
python3 growth/check-motion.py
python3 -m unittest tests.test_all.DocsMatchReality -q
```

CI checks dimensions, duration, size, media fallbacks, and the silent player.
The MP4 budget is below GitHub's 10 MB free-plan video attachment limit.
The image encoders follow the documented [Sharp animation options](https://sharp.pixelplumbing.com/api-output/).
GitHub's [attachment documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files)
describes native video uploads. Repository GIF/WebP previews remain available
without a separate video attachment.

No conversion lift, universal editing quality, or processing-speed claim is made.
