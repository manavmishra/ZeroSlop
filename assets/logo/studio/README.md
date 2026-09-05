# Zero Slop logo kit

The supplied logo is the source of truth: a gold rounded square, black Z, and rust stroke. The vector master reconstructs that logo without redesigning it. The original uploaded PNG is preserved unchanged as `zero-slop-logo-original.png`.

## Files

- `zero-slop-logo-original.png`: unmodified supplied 192 × 192 PNG.
- `zero-slop-mark.svg`: editable vector reconstruction of that logo.
- `zero-slop-wordmark.svg`: optional secondary outlined lettering, not part of the supplied logo.
- `zero-slop-lockup.svg`: supplied mark beside the optional name treatment.
- `zero-slop-mark-300-white.png`: exact 300 × 300 PNG on white.
- `zero-slop-mark-300-transparent.png`: exact 300 × 300 PNG with alpha.
- `zero-slop-mark-1200-white.png` and `zero-slop-mark-1200-transparent.png`: larger exports.
- `zero-slop-lockup-1600-white.png`: horizontal PNG.
- `zero-slop-logo-review.png`: local review sheet, not a logo master.
- `zero-slop-mark-3d-1200.png`: 1200 × 1200 physically based studio render on white.

The SVG masters can be imported into Figma, Illustrator, Affinity Designer, or Blender. They were constructed as editable vectors, not designed inside those applications. The Z follows the original repository path without the enlarged-mark transform. The stroke geometry was fitted against the supplied PNG. The optional lettering needs no external font.

## Use

Use the supplied colors: gold `#e2a500`, ink `#12100c`, and rust `#8c3f22`. Preserve the gold tile and its rounded corners. The 64-unit SVG canvas uses corner radius 17. Use the mark at 24 CSS pixels or larger. Keep the optional horizontal lockup at least 170 pixels wide.

Keep the flat master free of gradients, shadows, bevels, and textures. Materials and lighting may be applied in a 3D scene without changing the vector geometry. Do not stretch the mark or crop the gold tile. The white PNG fills only the area outside the rounded corners; the transparent PNG keeps that area transparent. Both retain the gold background.

Rebuild the exports from the repository root with:

```sh
node assets/logo/studio/build.mjs
```

The build uses the repository's existing Sharp dependency and verifies export dimensions and alpha modes. Existing logos outside this directory are unchanged.

Rebuild the 3D PNG with `node growth/export-studio-logo.mjs`, using the build-only Three.js dependencies described in `growth/motion-design.md`.
