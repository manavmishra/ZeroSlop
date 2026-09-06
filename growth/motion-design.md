# Zero Slop README shell demo

The README uses the dark terminal animation that was live on September 4,
2026. The original GIF is restored byte for byte. It runs for 15.15 seconds
at 900 × 580 pixels, with 34 distinct frames and their original reading holds.
The background is charcoal (`#1b1a18`), with a slightly lighter title bar,
light text, and amber, rust and green highlights. There is no audio.

This is a reconstructed command session drawn by an HTML renderer. Commands
type in; output appears as complete lines. Its edited timing does not measure
installation, scoring or model latency. Your AI assistant performs the edit;
the local meter scores the writing and checks tracked source details.

## What the demo shows

1. Install with `npx zero-slop install`.
2. Run `zero-slop score post.md`: the historical draft scores 100.0, with
   11 flagged phrases across 83 words.
3. Read five example flags, including stock announcements, promotional
   adjectives and a formulaic contrast.
4. Invoke `/zero-slop post.md` and show the source-check result, `40% held`.
5. Finish at 9.5, with zero flagged phrases across 10 words.

The historical draft is longer than the current README's before-and-after
example, which scores 99.3. These are separate examples. The restored animation
does not display the complete draft or edit. Its 40% figure belongs to the
sample claim; it is not a Zero Slop performance result, and preserving it does
not establish that the claim is true.

## Source and restoration

The September 4 repository state is commit `5b9ef28f`. Its GIF was last updated
in `91ee2fc1`, which aligned the rewrite's displayed score with the accompanying
README example. The restored master has Git blob
`dd642cbe7b73d06ceff3e2511a553bcfd244e369` and is 45,862 bytes.

`growth/demo-evidence.json` records the historical source, exact asset identity,
duration and example. `growth/shell-demo-source.mjs` preserves the original
HTML/Chromium and Sharp generator for inspection. It is build tooling and adds
no dependency to the installed skill. The committed GIF is the visual master;
regenerating it with different browser or font versions may produce different
pixels.

The WebP keeps the master's pixels and frame delays. The MP4 represents the
same 15.15-second sequence on a 20 fps grid: 303 frames, with source holds
preserved. Repeated video frames preserve those holds; they do not add motion
or change the animation's pace. The poster uses the final result frame.

## MCP connection

The historical animation contains no MCP address or hosted-product end card.
The README and HTML player provide the connection address separately:
`https://mcp.zero-slop.ai/mcp`. The [MCP setup guide](https://zero-slop.ai/#mcp)
explains how to connect. The media checks compare the documented address with
`server.json` and require the player to display it as text.

## Deliverables

| File in `assets/` | Purpose |
|---|---|
| `zero-slop-demo.gif` | Original 900 × 580 dark-shell animation, 34 frames, 15.15 seconds |
| `zero-slop-demo.webp` | Lossless inline version with the same pixels and timing |
| `zero-slop-demo.mp4` | Silent 900 × 580 H.264 video, 20 fps, 303 frames, fast-start |
| `zero-slop-demo-poster.png` | 900 × 580 final-result still for reduced motion |
| `zero-slop-demo.html` | Manual-play video, text transcript and MCP connection address |

The README selects the still for reduced-motion preferences, then WebP, then
GIF. It specifies width without a fixed height so the terminal retains its
original aspect ratio. The player exposes native pause, seek and replay
controls and waits for the viewer to start playback.

The supplied gold logo and its local exports remain available in
`assets/logo/studio/`. They are separate assets from this restored animation.

## Rebuild the derivatives

`growth/export-shell-media.mjs` verifies the original GIF's hash, then exports
the lossless WebP, final-frame poster and silent MP4. It needs Node.js, Sharp
and FFmpeg as build tools. Set `ZERO_SLOP_FFMPEG` if FFmpeg is not on `PATH`.
Write to a temporary output directory and inspect the results before replacing
the published assets:

```sh
git show 5b9ef28f:assets/zero-slop-demo.gif > /tmp/zero-slop-original-shell.gif
node growth/export-shell-media.mjs \
  /tmp/zero-slop-original-shell.gif /tmp/zero-slop-shell-export
```

## Verification and archived production files

Run the active media and documentation checks after any change:

```sh
python3 growth/check-motion.py
node growth/verify-demo-player.mjs
python3 -m unittest tests.test_all.DocsMatchReality -q
```

The media checks cover the original GIF's identity, dimensions, duration,
derivative timing, absence of audio, README fallbacks, manual playback, and
the documented MCP address. Inspect the result frame and play the video to
confirm that the command sequence and reading holds survived conversion.

Earlier studio-production sources remain in `growth/` for reference. They do
not generate the active README animation. In particular,
`growth/check-studio-cadence.mjs` validates the archived studio timeline only;
passing that check says nothing about the restored shell demo. Any future
studio render should write to separate output paths until deliberately
selected for publication.

The restored animation makes no claim about conversion lift, universal editing
quality or processing speed.
