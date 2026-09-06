#!/usr/bin/env node
// Maintainer-only: derive web formats from the exact September 4 GIF master.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {copyFile, mkdir, readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require = createRequire(import.meta.url);
const sharp = require('sharp');
const [input, destination] = process.argv.slice(2);
assert(input && destination, 'Usage: node growth/export-shell-media.mjs ORIGINAL.gif OUTPUT_DIRECTORY');
const bytes = await readFile(input);
const blob = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
assert.equal(blob, 'dd642cbe7b73d06ceff3e2511a553bcfd244e369', 'Input differs from the September 4 GIF');
const metadata = await sharp(bytes, {animated: true}).metadata();
assert.equal(metadata.pages, 34);
assert.equal(metadata.delay.reduce((a, b) => a + b, 0), 15150);
await mkdir(destination, {recursive: true});
const output = name => resolve(destination, `zero-slop-demo${name}`);
await copyFile(input, output('.gif'));
await sharp(bytes, {page: 33, pages: 1}).png().toFile(output('-poster.png'));
await sharp(bytes, {animated: true})
  .webp({lossless: true, loop: 0, delay: metadata.delay})
  .toFile(output('.webp'));
const ffmpeg = process.env.ZERO_SLOP_FFMPEG || 'ffmpeg';
execFileSync(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-y', '-i', resolve(input),
  '-vf', 'fps=20', '-frames:v', '303', '-an', '-c:v', 'libx264', '-preset', 'slow',
  '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', output('.mp4')], {stdio: 'inherit'});
console.log('Restored original GIF; derived silent 15.15-second MP4, lossless WebP, and final-frame poster.');
