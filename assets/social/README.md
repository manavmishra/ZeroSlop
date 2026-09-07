# Approved share artwork

Manav supplied and approved these two PNGs on September 6, 2026. Both originals
are preserved unchanged, including their layout and embedded text.

| File | Dimensions | Use |
| --- | --- | --- |
| `zero-slop-github-preview-1280x640.png` | 1280 × 640 | GitHub and full-size link previews |
| `zero-slop-github-preview-640x320.png` | 640 × 320 | Compact and mobile sharing |

`assets/social-preview.png` is an exact copy of the 1280 × 640 master. Restore
that compatibility path with `node growth/make-social-preview.mjs`. The command
copies the approved file; it does not redraw, resize, or recompress it. Use the
supplied smaller file when a compact version is needed.

`python3 growth/check-motion.py` verifies both original file hashes, dimensions,
and the compatibility copy. See [the official brand page](https://zero-slop.ai/brand/)
for the current public download kit.
