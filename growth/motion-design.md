# Zero Cut motion assets

The GitHub visual is a silent, white-background product film. It uses the
repository's black Z and rust slash, preserved in `assets/logo/logo-mark.svg`.
The slash is the transition between the flagged draft and its edit.

The 8.4-second sequence opens on “We're thrilled to…”, reveals the complete
draft, makes the cut, holds the edited sentence, and ends on the free editor
at `https://zero-slop.ai/try/`. The 40% result stays fixed during the edit.
The scores, 99.3 and 9.5, come from the repository's example; playback timing
does not claim product latency or editing speed.

## Exports

| File in `assets/` | Use |
|---|---|
| `zero-slop-demo.webp` | Preferred GitHub image for supporting browsers |
| `zero-slop-demo.gif` | Compatible animation fallback; existing URL preserved |
| `zero-slop-demo-poster.png` | Reduced-motion still |
| `zero-slop-demo.html` | Standalone player with pause/replay and responsive sizing |
| `logo/logo-300.png` | Exact 300 × 300 logo on white |
| `logo/logo-mark-300.png` | Exact 300 × 300 logo with transparency |
| `logo/logo-mark.svg` | Shared vector source |

The README makes the whole visual a link to the free editor. Its `<picture>`
selects the still first for reduced-motion preferences, then WebP, then GIF.
The player has no external scripts, fonts, requests, or audio. It suspends
playback in a hidden tab and stops its frame loop when paused or motion is reduced.

## Rebuild and check

The asset generators need Node.js, Chrome, `playwright-core`, and `sharp` at
build time. They add no dependencies to the published skill. Use `CHROME_PATH`
for a non-default Chrome location and `NODE_PATH` for external build packages.
The logo exporter also accepts `ZERO_SLOP_NODE_MODULES`.

```sh
node growth/make-logo.mjs
node scripts/make-readme-gif.mjs
python3 growth/check-motion.py
```

Long holds cost one frame each; the short transitions use 25 fps. The
standalone player renders at the display's refresh rate. Both image formats
have a 400 kB ceiling, checked in CI. Each must encode exactly 8,400 ms.
Visible scenes and score labels switch without overlapping text.

The rendering choices follow the documented [Sharp animation options](https://sharp.pixelplumbing.com/api-output/)
and browser [`picture` source selection](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/picture).
No conversion uplift is claimed without a traffic-controlled test.
