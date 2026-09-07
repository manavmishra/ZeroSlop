#!/usr/bin/env node
// Copy the approved 1280x640 share artwork without rendering or recompressing it.
// Usage: node growth/make-social-preview.mjs [outfile]
// The separate approved 640x320 version is preserved in assets/social/.

import { copyFile, mkdir, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const master = resolve(root, "assets/social/zero-slop-github-preview-1280x640.png");
const out = process.argv[2] ? resolve(process.argv[2]) : resolve(root, "assets/social-preview.png");
if (process.argv.length > 3) throw new Error("Usage: node growth/make-social-preview.mjs [outfile]");

const bytes = await readFile(master);
const signature = Buffer.from("89504e470d0a1a0a", "hex");
if (bytes.length < 24 || !bytes.subarray(0, 8).equals(signature) ||
    bytes.readUInt32BE(16) !== 1280 || bytes.readUInt32BE(20) !== 640) {
  throw new Error("The approved share master must be a 1280x640 PNG.");
}
await mkdir(dirname(out), { recursive: true });
await copyFile(master, out);
console.log(`copied approved artwork to ${out} (${bytes.length} bytes, 1280x640)`);
