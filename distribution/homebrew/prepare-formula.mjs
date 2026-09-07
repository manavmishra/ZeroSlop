#!/usr/bin/env node
// Maintainer-only release helper. It never publishes or installs anything.
import { createHash, timingSafeEqual } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const VERSION = "2.10.1";
export const METADATA_URL = `https://registry.npmjs.org/zero-slop/${VERSION}`;
export const TARBALL_URL = `https://registry.npmjs.org/zero-slop/-/zero-slop-${VERSION}.tgz`;
const ROOT = dirname(fileURLToPath(import.meta.url));
const CHECKSUM_PLACEHOLDER = "__NPM_TARBALL_SHA256__";

export async function prepareFormula(output, fetchRelease = fetch) {
  const options = { redirect: "error", signal: AbortSignal.timeout(30_000) };
  const metadataResponse = await fetchRelease(METADATA_URL, options);
  if (!metadataResponse.ok) {
    throw new Error(`Published npm metadata unavailable (HTTP ${metadataResponse.status}); no formula generated.`);
  }
  const metadata = await metadataResponse.json();
  if (metadata.name !== "zero-slop" || metadata.version !== VERSION || metadata.dist?.tarball !== TARBALL_URL) {
    throw new Error(`npm metadata does not identify the exact zero-slop ${VERSION} tarball.`);
  }
  const integrity = /^sha512-([A-Za-z0-9+/]+={0,2})$/.exec(metadata.dist.integrity ?? "");
  if (!integrity || Buffer.from(integrity[1], "base64").length !== 64) {
    throw new Error("Published npm metadata must include a SHA-512 integrity value.");
  }
  const tarballResponse = await fetchRelease(TARBALL_URL, {
    redirect: "error", signal: AbortSignal.timeout(30_000),
  });
  if (!tarballResponse.ok) throw new Error(`Published npm tarball unavailable (HTTP ${tarballResponse.status}).`);
  const tarball = Buffer.from(await tarballResponse.arrayBuffer());
  if (!timingSafeEqual(createHash("sha512").update(tarball).digest(), Buffer.from(integrity[1], "base64"))) {
    throw new Error("Downloaded tarball does not match npm's published SHA-512 integrity value.");
  }
  const sha256 = createHash("sha256").update(tarball).digest("hex");
  const template = await readFile(resolve(ROOT, "zero-slop.rb.in"), "utf8");
  if (template.split(CHECKSUM_PLACEHOLDER).length !== 2) throw new Error("Formula template must contain exactly one checksum placeholder.");
  const formula = template.replace(CHECKSUM_PLACEHOLDER, sha256).replace(/^# Release template\..*\n/, "");
  await mkdir(dirname(resolve(output)), { recursive: true });
  await writeFile(output, formula, { flag: "wx" });
  return { version: VERSION, tarball: TARBALL_URL, sha256, output: resolve(output) };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 3) {
    console.error("Usage: node distribution/homebrew/prepare-formula.mjs <new-output.rb>");
    process.exitCode = 2;
  } else {
    try {
      console.log(JSON.stringify(await prepareFormula(process.argv[2]), null, 2));
    } catch (error) {
      console.error(error.message);
      process.exitCode = 1;
    }
  }
}
