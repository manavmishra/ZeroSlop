# Zero Slop product demo

A silent, 24-second Blender product film of the installed Agent Skill. The
supplied gold-tile logo opens the film in three dimensions. A physical terminal
housing then carries the installation, assistant request, complete draft, edit,
and local checks. The opening is a depth-occluded handoff: the bezel passes in
front of the mark instead of using a translucent crossfade. There is no audio
track, music or sound effect.

Blender 5.2.1 LTS (Eevee) renders the physical materials, lighting, shadows,
camera movement and transitions. The screen texture is captured from a real
xterm.js character grid, including its ANSI styling and scrollback. This is a
reconstruction of the saved launch-post example, not a recording of the hosted
editor or a latency measurement. Different host models can return different
edits.

The shell direction comes from commit `91ee2fc1`. The current treatment keeps
the supplied gold-tile logo from `assets/logo/studio/`, white studio background
and rust accent, with larger terminal type and a clear distinction between the
shell and the AI assistant.

## The story

| Time | Viewer sees |
|---|---|
| 0-1.8 s | The gold-tile logo rests on white; the terminal enters from depth and physically occludes it |
| 1.8-2.8 s | The camera settles; the installation state holds in the terminal |
| 2.8-5.0 s | The context changes to the AI assistant; `/zero-slop` is entered |
| 5.0-8.5 s | The complete source arrives as a paste and stays readable |
| 8.5-13.0 s | Four actual phrase flags appear as whole output lines |
| 13.0-17.0 s | The edit arrives and the rust accent carries the eye to the retained `40%` detail |
| 17.0-20.7 s | Source-detail and writing checks hold beneath the full edit |
| 20.7-24.0 s | The terminal recedes beside the logo; the exact MCP endpoint and browser option remain on screen |

The original's 40% claim is a sample claim, not a Zero Slop performance result.
The scorer is rerun during rendering: 99.3 becomes 9.5, with four flagged phrases
becoming zero. The source check is also rerun. Its result concerns tracked
details; it does not establish that the original claim is true.

`growth/demo-evidence.json` records exact texts, source hashes, and full tool
output. It also identifies the Blender renderer and the canonical MCP URL.
`growth/blender-readme-film.py` owns the deterministic scene and presentation
clock. `growth/blender-screens/` contains the exact xterm plates used by the
screen material. Only user commands are typed character by character in the
source capture; machine output arrives in complete lines, and Blender holds the
camera while the viewer reads. No fabricated processing time or check animation
implies independent reviews.

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

The terminal housing and logo use Blender Principled materials for controlled
roughness, metallic reflections, bevel response and a light clear coat. A warm
soft key, cool fill and edge reflection shape a white cyc; the floor keeps only a
soft contact shadow. The terminal face stays opaque/emissive so a highlight
cannot hide the draft. The imported screen plates remain sRGB image textures and
are never recreated with Blender fonts.

The opening moves from the mark into the terminal with real depth ordering and
no visibility cut or camera jump. Camera movement is confined to entry and the
closing view; the reading sections stay steady. Bezier easing brings each move
to rest, and the screen swaps through a short 12-frame handoff while preserving
whole readable states. Static reading holds keep the GitHub animation compact.

The MP4 is encoded from 720 evenly spaced Blender frames, one for every 30 fps
output frame. Transcript timing never changes the camera's clock. The bundled
Blender build has no FFmpeg encoder, so Blender writes the PNG sequence and the
maintainer-only `growth/encode-blender-film.py` wrapper performs the silent H.264
mux with imageio-ffmpeg. This keeps scene authorship and delivery encoding
separate and verifiable.

## Deliverables

| File in `assets/` | Purpose |
|---|---|
| `zero-slop-demo.mp4` | Silent 24-second, 1920 × 1080, 30 fps H.264 Blender film, fast-start |
| `zero-slop-demo.webp` | 960 × 540 inline GitHub animation |
| `zero-slop-demo.gif` | Compatible inline fallback, existing URL preserved |
| `zero-slop-demo-poster.png` | 1280 × 720 result-and-checks still for reduced motion |
| `zero-slop-demo.html` | Native video player with controls and a text transcript |
| `logo/studio/zero-slop-mark-300-white.png` | Supplied gold logo, 300 × 300 on white |
| `logo/studio/zero-slop-mark-300-transparent.png` | Supplied gold logo, 300 × 300 with transparent corners |
| `logo/studio/zero-slop-mark.svg` | Editable vector reconstruction of the supplied logo |
| `logo/studio/zero-slop-mark-3d-1200.png` | 1200 × 1200 studio logo render |

The README's picture selects the still for reduced-motion preferences, then
WebP, then GIF. Only width is specified: GitHub's maximum-width styling would
distort a fixed-height image. The MP4 player never autoplays and exposes native
pause, seek and replay controls. MP4, GIF and WebP are silent. The player's
transcript explains the source check.

The preferred WebP is a silent 6 fps, 960 × 540 export under the 2 MB budget.
The compatible GIF is a silent 4 fps, 28-colour, 960 × 540 fallback under the
2.5 MB budget; WebP carries the smoother inline presentation. Both preserve the
24-second timeline and still-frame holds between animated intervals.

## Rebuild

Build-time dependencies for the original terminal plate capture are Node.js,
Chrome, `playwright-core` 1.55.0, `sharp` 0.34.5, `esbuild` 0.28.0 and
`@xterm/xterm` 6.0.0. They add nothing to the published skill. Blender 5.2.1
LTS is required for scene rendering. MP4 encoding uses the maintainer's
`imageio-ffmpeg` binary (or `ffmpeg` on PATH); no encoder is shipped in the
repository.

```sh
# Keep media dependencies outside the skill's dependency-free runtime.
npm install --prefix /tmp/zero-slop-media-deps --ignore-scripts \
  @xterm/xterm@6.0.0 esbuild@0.28.0 \
  playwright-core@1.55.0 sharp@0.34.5
NODE_PATH=/tmp/zero-slop-media-deps/node_modules \
ZERO_SLOP_MEDIA_DEPS=/tmp/zero-slop-media-deps \
  node growth/export-terminal-screens.mjs

# In Blender's Python Console or Text Editor, run the scene builder:
#   growth/blender-readme-film.py -- --frames /tmp/zero-slop-blender-frames
python3 growth/encode-blender-film.py \
  --frames /tmp/zero-slop-blender-frames \
  --output /tmp/zero-slop-demo-new.mp4
```

The encoder refuses an incomplete sequence. Inspect the new MP4 before replacing
`assets/zero-slop-demo.mp4`. Use the Blender script's `--preview` flag to render
frame 390 before the complete export. PNG frames are 1080p. The six screen
plates can be regenerated with the capture helper; they are never retyped in
Blender. The GIF and WebP timeline samples the finished MP4 and stays silent.

```sh
python3 growth/check-motion.py
node growth/check-studio-cadence.mjs \
  --manifest /tmp/zero-slop-film-frames/manifest.json \
  --inspections /tmp/zero-slop-film-frames/motion-inspections.json
node growth/verify-demo-player.mjs
ZERO_SLOP_MEDIA_DEPS=/tmp/zero-slop-media-deps node growth/check-studio-scroll.mjs
python3 -m unittest tests.test_all.DocsMatchReality -q
```

CI checks dimensions, duration, size, media fallbacks, the absence of audio and
manual playback controls.
The cadence check also verifies the exact output grid, finite and continuous
motion, easing endpoints, projected screen-corner movement and static preview
holds. These numerical checks complement visual review of the encoded movie;
they do not measure production taste.
The MP4 budget is below GitHub's 10 MB free-plan video attachment limit.
The image encoders follow the documented [Sharp animation options](https://sharp.pixelplumbing.com/api-output/).
GitHub's [attachment documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files)
describes native video uploads. Repository GIF/WebP previews remain available
without a separate video attachment.

No conversion lift, universal editing quality, or processing-speed claim is made.
