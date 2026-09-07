#!/usr/bin/env node
// Maintainer-only compatibility exports of the official supplied identity.
// The canonical SVG and PNG files in assets/logo remain byte-for-byte unchanged.
// Usage: node growth/make-logo.mjs [outdir] [--all]
// Requires Sharp; ZERO_SLOP_NODE_MODULES may select an existing dependency directory.

import { copyFile, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const sharp = require(process.env.ZERO_SLOP_NODE_MODULES
  ? resolve(process.env.ZERO_SLOP_NODE_MODULES, "sharp")
  : "sharp");
const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourceDir = resolve(repoRoot, "assets/logo");
const outDir = resolve(process.argv.slice(2).find((arg) => arg !== "--all") ?? sourceDir);
const sizes = process.argv.includes("--all") ? [300, 512, 1024] : [300];
const mark = resolve(sourceDir, "zero-slop-mark-orange.svg");

await mkdir(outDir, { recursive: true });
await copyFile(mark, resolve(outDir, "logo-mark.svg"));

for (const size of sizes) {
  for (const transparent of [false, true]) {
    const name = `logo-${transparent ? "mark-" : ""}${size}.png`;
    const output = resolve(outDir, name);
    if (size === 300 && !transparent) {
      await copyFile(resolve(sourceDir, "zero-slop-github-300.png"), output);
    } else if (size === 512 && transparent) {
      await copyFile(resolve(sourceDir, "zero-slop-app-icon-transparent-512.png"), output);
    } else {
      let raster = sharp(mark, { density: 300 }).resize(size, size);
      if (!transparent) raster = raster.flatten({ background: "#FBFAF7" });
      await raster.png({ compressionLevel: 9 }).toFile(output);
    }
    const metadata = await sharp(output).metadata();
    if (metadata.width !== size || metadata.height !== size) {
      throw new Error(`${name}: incorrect dimensions`);
    }
    console.log(`wrote ${output} (${size}x${size}, official rust mark)`);
  }
}
