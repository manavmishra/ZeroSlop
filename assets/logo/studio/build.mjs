#!/usr/bin/env node
// Maintainer-only faithful export of the supplied logo. No runtime assets change.
// Run: node assets/logo/studio/build.mjs
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const dir = dirname(fileURLToPath(import.meta.url));
const mark = await readFile(resolve(dir, 'zero-slop-mark.svg'), 'utf8');
const wordmark = await readFile(resolve(dir, 'zero-slop-wordmark.svg'), 'utf8');
const content = svg => svg.slice(svg.indexOf('>') + 1, svg.lastIndexOf('</svg>'))
  .replace(/\s*<(title|desc)\b[^>]*>[\s\S]*?<\/\1>/g, '')
  .replace(/\s+id="[^"]*"/g, '');
const svg = (width, height, body, label) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${label}">${body}</svg>\n`;
const markBody = content(mark);
const wordBody = content(wordmark);

// Align the supplied gold tile with the optional secondary wordmark.
const lockup = svg(550, 132,
  `<g transform="translate(0 2) scale(2)">${markBody}</g>` +
  `<g transform="translate(149 11) scale(1.08)">${wordBody}</g>`, 'Zero Slop');
await writeFile(resolve(dir, 'zero-slop-lockup.svg'), lockup);

for (const size of [300, 1200]) {
  for (const background of ['transparent', 'white']) {
    let pipeline = sharp(Buffer.from(mark), { density: 600 }).resize(size, size);
    if (background === 'white') pipeline = pipeline.flatten({ background: '#ffffff' });
    const name = `zero-slop-mark-${size}-${background}.png`;
    await pipeline.png({ compressionLevel: 9 }).toFile(resolve(dir, name));
    console.log(`wrote ${name}`);
  }
}
await sharp(Buffer.from(lockup), { density: 300 }).resize({ width: 1600 })
  .flatten({ background: '#ffffff' }).png({ compressionLevel: 9 })
  .toFile(resolve(dir, 'zero-slop-lockup-1600-white.png'));

// A local review sheet. Labels are documentation, never baked into the masters.
const sheet = svg(1600, 1050,
  `<rect width="1600" height="1050" fill="#ffffff"/>` +
  `<g transform="translate(174 120) scale(2.22)">${content(lockup)}</g>` +
  `<path d="M124 515H1476" stroke="#e9e6e2"/>` +
  `<g transform="translate(165 615) scale(4.5)">${markBody}</g>` +
  `<g transform="translate(640 651) scale(3.5)">${markBody}</g>` +
  `<g transform="translate(1160 722) scale(1.25)">${markBody}</g>` +
  `<g fill="#68645e" font-family="Arial, sans-serif" font-size="21">` +
  `<text x="174" y="965">Vector master</text>` +
  `<text x="649" y="965">300 × 300 export</text>` +
  `<text x="1129" y="965">Small-size check</text></g>`, 'Zero Slop logo review');
await sharp(Buffer.from(sheet)).png({ compressionLevel: 9 })
  .toFile(resolve(dir, 'zero-slop-logo-review.png'));

for (const size of [300, 1200]) {
  for (const background of ['transparent', 'white']) {
    const name = `zero-slop-mark-${size}-${background}.png`;
    const metadata = await sharp(resolve(dir, name)).metadata();
    if (metadata.width !== size || metadata.height !== size) throw new Error(`${name}: incorrect dimensions`);
    if (metadata.hasAlpha !== (background === 'transparent')) throw new Error(`${name}: incorrect alpha mode`);
  }
}
console.log('Logo exports verified: exact dimensions and alpha modes.');
