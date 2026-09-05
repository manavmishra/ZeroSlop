# Zero Slop product demo

A silent, 24-second studio film of the installed Agent Skill. The supplied
gold-tile logo opens the film in three dimensions. The camera then moves to a
white terminal housing for the installation, assistant request, complete draft,
edit, and local checks. The opening overlaps the logo and terminal; the camera
settles before the reading sections. There is no audio track, music or sound
effect.

Three.js renders the physical materials, lighting, shadows and camera movement.
The screen texture is captured from a real xterm.js character grid, including its
ANSI styling, cursor and scrollback. This is a reconstruction of the saved
launch-post example, not a screen recording, a Blender render, or a latency
measurement. Different host models can return different edits.

The shell direction comes from commit `91ee2fc1`. The current treatment keeps
the supplied gold-tile logo from `assets/logo/studio/`, white studio background
and rust accent, with larger terminal type and a clear distinction between the
shell and the AI assistant.

## The story

| Time | Viewer sees |
|---|---|
| 0-1.2 s | The gold-tile logo and product promise transition into the terminal, with an overlapping fade |
| 1.2-3.6 s | The camera settles; the installation command finishes typing |
| 3.6-5 s | The context changes to the AI assistant; `/zero-slop` is entered |
| 5-8.6 s | The complete source arrives as a paste and stays readable |
| 8.6-11.2 s | Four actual phrase flags appear as whole output lines |
| 11.2-15.8 s | The edit arrives; the rust signature briefly underlines it |
| 15.8-19 s | Source-detail and writing checks finish beneath the full edit |
| 19-24 s | The terminal recedes beside the logo; the exact MCP endpoint and browser option remain on screen |

The original's 40% claim is a sample claim, not a Zero Slop performance result.
The scorer is rerun during rendering: 99.3 becomes 9.5, with four flagged phrases
becoming zero. The source check is also rerun. Its result concerns tracked
details; it does not establish that the original claim is true.

`growth/demo-evidence.json` records exact texts, source hashes, and full tool
output. It also identifies both renderers and the canonical MCP URL.
`growth/demo-film.mjs` owns the terminal transcript.
`growth/studio-timeline.mjs` maps the transcript to the studio cut and exposes
the camera and object motion as a pure function of presentation time.
`growth/studio-scene.mjs` applies that state to the three-dimensional set.
Only user commands are typed character by character. Machine output arrives in
complete lines; the camera holds while the viewer reads. No fabricated
processing time or check animation implies independent reviews.

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

The terminal housing and logo use Three.js
[physical materials](https://threejs.org/docs/pages/MeshPhysicalMaterial.html)
for controlled roughness, metallic reflections and a light clear coat.
[RoomEnvironment](https://threejs.org/docs/pages/RoomEnvironment.html)
provides environment lighting through a prefiltered map. The terminal face stays
unlit, so a specular highlight cannot hide the draft. Following Three.js's
[color-management guidance](https://threejs.org/manual/en/color-management.html),
the PNG texture is marked as sRGB and the display output uses sRGB. Lighting and
tone mapping affect the housing, not the source text.

The opening moves from the mark into the terminal without a visibility cut or
camera jump. Camera movement is confined to entry and the closing view; the
reading sections stay steady. Minimum-jerk easing brings each move to rest with
zero endpoint velocity and acceleration. The terminal scrolls through new
output over 220 ms instead of jumping whole rows. Static reading holds also
keep the GitHub animation compact.

The MP4 is rendered at 720 evenly spaced presentation timestamps, one for every
30 fps output frame. Transcript retiming never changes the camera's clock.
The previous sparse, source-timed export lost 66 of its 240 rendered samples
when the encoder quantized their durations. Sampling the final clock removes
that source of uneven motion; increasing the advertised frame rate alone would
not have repaired it.

## Deliverables

| File in `assets/` | Purpose |
|---|---|
| `zero-slop-demo.mp4` | Silent 24-second, 1920 × 1080, 30 fps H.264 film, fast-start |
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

The preferred WebP has a 2 MB budget. The 24 fps GIF fallback has a 2.5 MB
budget so its motion need not lose frames to meet the previous 12 fps export's
size cap. Both use still-frame holds between animated intervals.

## Rebuild

Build-time dependencies are Node.js, Chrome, `playwright-core` 1.55.0, `sharp`
0.34.5, `esbuild` 0.28.0, `@xterm/xterm` 6.0.0, and `three` 0.180.0.
They add nothing to the published skill. `CHROME_PATH` can select an existing
Chrome installation. `NODE_PATH` resolves the capture tools;
`ZERO_SLOP_MEDIA_DEPS` resolves the terminal renderer and Three.js bundle.
MP4 encoding uses macOS AVFoundation through Swift and requires Apple's
command-line tools; no codec package is installed.

```sh
# Keep media dependencies outside the skill's dependency-free runtime.
npm install --prefix /tmp/zero-slop-media-deps --ignore-scripts \
  @xterm/xterm@6.0.0 three@0.180.0 esbuild@0.28.0 \
  playwright-core@1.55.0 sharp@0.34.5
NODE_PATH=/tmp/zero-slop-media-deps/node_modules \
ZERO_SLOP_MEDIA_DEPS=/tmp/zero-slop-media-deps \
  node scripts/make-readme-gif.mjs --frames /tmp/zero-slop-film-frames
swift -module-cache-path /tmp/zero-slop-swift-cache growth/encode-demo.swift \
  --manifest /tmp/zero-slop-film-frames/manifest.json \
  --output /tmp/zero-slop-demo-new.mp4 \
  --width 1920 --height 1080 --fps 30 --bitrate 8000000
```

The native encoder uses an 8 Mbps target and refuses to overwrite an existing
output. Inspect the new MP4 before replacing `assets/zero-slop-demo.mp4`.
Use `--preview` with the Node command to render key scenes before the complete
export. PNG frames are 1080p. The manifest records every frame's exact
presentation timestamp and 1/30-second duration. Terminal textures can be reused
when their visible content is unchanged, but the film's frame grid is never
thinned or retimed. The GIF and WebP timeline samples movement on a separate
24 fps presentation grid and holds only still scenes. GIF delays are quantized
cumulatively to its 10 ms timebase, preserving the 24-second duration.

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
