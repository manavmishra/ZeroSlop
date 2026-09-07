#!/usr/bin/env node
// Copy the canonical website press captures into the repository's directory kit.
// These images are owned by the live site; this command never redraws its logo,
// terminal example, benchmark, or workflow diagram.
// Usage: node growth/make-screenshots.mjs [outdir]
// Before a site deploy: node growth/make-screenshots.mjs --source-dir ZSWebpage/public/press
// SITE may select an explicitly chosen preview deployment.

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
let outDir = resolve(root, "assets/screenshots");
let sourceDir;
let outputSelected = false;
for (let index = 0; index < args.length; index += 1) {
  if (args[index] === "--source-dir") {
    if (!args[index + 1]) throw new Error("--source-dir requires a directory");
    sourceDir = resolve(args[++index]);
  } else if (args[index].startsWith("--") || outputSelected) {
    throw new Error("Usage: node growth/make-screenshots.mjs [outdir] [--source-dir directory]");
  } else {
    outDir = resolve(args[index]);
    outputSelected = true;
  }
}
const site = new URL(process.env.SITE ?? "https://zero-slop.ai/");
const names = ["01-hero.png", "02-rewrite.png", "03-terminal.png", "04-benchmark.png", "05-engine.png"];
const signature = Buffer.from("89504e470d0a1a0a", "hex");
const captures = [];

for (const name of names) {
  let bytes;
  if (sourceDir) {
    bytes = await readFile(resolve(sourceDir, name));
  } else {
    const url = new URL("/press/" + name, site);
    const response = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(30000) });
    if (!response.ok || !response.headers.get("content-type")?.startsWith("image/png")) {
      throw new Error("Could not load canonical PNG: " + url + " (HTTP " + response.status + ")");
    }
    bytes = Buffer.from(await response.arrayBuffer());
  }
  if (bytes.length < 24 || bytes.length > 20_000_000 || !bytes.subarray(0, 8).equals(signature)) {
    throw new Error("Invalid or oversized press PNG: " + name);
  }
  const width = bytes.readUInt32BE(16), height = bytes.readUInt32BE(20);
  if (!width || !height || width > 12000 || height > 12000) {
    throw new Error("Unexpected press PNG dimensions: " + name);
  }
  captures.push({ name, bytes, width, height });
}

// Validate the complete set before replacing any existing image.
await mkdir(outDir, { recursive: true });
for (const { name, bytes, width, height } of captures) {
  await writeFile(resolve(outDir, name), bytes);
  console.log(`wrote ${name} (${width}x${height}, canonical press capture)`);
}
