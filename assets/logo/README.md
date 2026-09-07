# Official Zero Slop logo kit

These are the official assets supplied by Manav on September 6, 2026.
The SVG paths and supplied PNGs are preserved unchanged. The canonical download
page is [zero-slop.ai/brand](https://zero-slop.ai/brand/).

| Asset | Use |
| --- | --- |
| `zero-slop-logo-primary.svg` / `.png` | Full logo on a light background |
| `zero-slop-logo-reversed.svg` / `.png` | Full logo on a dark background |
| `zero-slop-mark-orange.svg` | Standalone rust mark |
| `zero-slop-github-300.png` | Supplied 300 × 300 mark on warm paper; filename normalized from `zero-slop-github-300(1).png` |
| `zero-slop-app-icon-transparent-512.png` | Supplied transparent 512 × 512 app icon |

Use rust `#C15732`, ink `#141412`, warm paper `#FBFAF7`, and CTA green `#17634F`.
Keep the supplied geometry, proportions, and colors. Use the primary and reversed
variants as supplied; do not redraw the lettering or recolor the mark.

The older `logo-mark.svg` and `logo-*.png` / `logo-mark-*.png` paths are compatibility
exports of the current identity. Regenerate them with:

```sh
node growth/make-logo.mjs --all
```

The generator copies supplied assets where an exact-size version exists and
renders other PNG sizes from the unchanged official mark. It does not modify
the seven supplied master files. It requires Sharp as a maintainer dependency;
the installed skill has no new dependency.

The `studio/` directory retains obsolete gold-logo production references for
historical inspection. Its logo-export commands are retired. Do not use those
files in new publications or alter the preserved historical demo to match them.

## Next versioned plugin release

The published Codex manifest still uses `interface.brandColor: "#2B5BC7"`.
Change it to `"#C15732"` in the next normal versioned release. The repository's
release check classifies all plugin-manifest edits as runtime changes, so this
branding-only update preserves the v2.9.1 manifest and does not publish a new
package. The official logo files are available independently of that setting.
