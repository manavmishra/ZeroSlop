# Zero Slop product demo

A silent, 36-second walkthrough of the installed Agent Skill. It shows where
to install it, what to ask an assistant, and how to read the resulting edit.
The footage is typeset from the repository's saved launch-post example; it is
not a screen recording of the hosted editor. Different host models can return
different edits.

## The story

| Time | Viewer sees |
|---|---|
| 0–5 s | The product's purpose and the exact installation command |
| 5–13 s | A `/zero-slop` request with the complete sample draft |
| 13–16.5 s | Four measured stock-phrase flags in that same draft |
| 16.5–17.2 s | The logo's rust slash makes the signature cut |
| 17.2–24 s | The complete edit, with the 40% result retained |
| 24–29.5 s | Original and edit together, with supporting writing scores |
| 29.5–36 s | The next-draft prompt, free browser editor, and hosted MCP |

The original's 40% claim is a sample claim, not a Zero Slop performance result.
The scorer is rerun during rendering: 99.3 becomes 9.5, with four flagged phrases
becoming zero. The source check is also rerun. Its result concerns tracked
details; it does not establish that the original claim is true.

`growth/demo-evidence.json` records exact texts, source hashes, and full tool
output. `growth/demo-film.mjs` owns the composition and timing. Every transition
serves an instruction or a change of state; holds leave time to read.

## Deliverables

| File in `assets/` | Purpose |
|---|---|
| `zero-slop-demo.mp4` | 1920 × 1080, 30 fps H.264 film, silent, fast-start |
| `zero-slop-demo.webp` | 960 × 540 inline GitHub animation |
| `zero-slop-demo.gif` | Compatible inline fallback, existing URL preserved |
| `zero-slop-demo-poster.png` | 1280 × 720 before/after still for reduced motion |
| `zero-slop-demo.html` | Native video player with controls and a text transcript |
| `logo/logo-300.png` | Existing 300 × 300 logo on white |
| `logo/logo-mark-300.png` | Existing 300 × 300 transparent logo |

The README's picture selects the still for reduced-motion preferences, then
WebP, then GIF. Only width is specified: GitHub's maximum-width styling would
distort a fixed-height image. The MP4 player never autoplays and exposes native
pause, seek, and replay controls. Its transcript also explains the source check.

## Rebuild

Build-time dependencies are Node.js, Chrome, `playwright-core`, and `sharp`.
They add nothing to the published skill. `CHROME_PATH` and `NODE_PATH` can
point to existing build tools. MP4 encoding uses macOS AVFoundation through
Swift and requires Apple's command-line tools; no codec package is installed.

```sh
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
