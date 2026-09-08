#!/usr/bin/env node
// Maintainer-only: package.json owns the release number. Never relabel benchmarks.
import { readFile, writeFile } from "node:fs/promises";

const root = new URL("../", import.meta.url);
const read = (path) => readFile(new URL(path, root), "utf8");
const version = JSON.parse(await read("package.json")).version;
if (!/^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/.test(version)) throw new Error("package.json must name a stable semantic version");
if (process.argv.slice(2).some((arg) => arg !== "--check")) throw new Error("Usage: node distribution/sync-version.mjs [--check]");
const check = process.argv.includes("--check");
const changes = [];
async function update(path, transform) {
  const before = await read(path);
  const after = transform(before);
  if (before !== after) changes.push({ path, after });
}
for (const path of [".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json", "gemini-extension.json", "server.json", "package-lock.json"]) {
  await update(path, (source) => {
    const data = JSON.parse(source);
    data.version = version;
    if (path === "package-lock.json") data.packages[""].version = version;
    return JSON.stringify(data, null, 2) + "\n";
  });
}
const rules = [
  ["SKILL.md", /(^\s*version:\s*")[0-9.]+(")/m, `$1${version}$2`],
  ["README.md", /(alt="Version )[0-9.]+(")/, `$1${version}$2`],
  ["README.md", /(badge\/version-)[0-9.]+(-72528F)/, `$1${version}$2`],
  ["README.md", /(npx --yes zero-slop@)[0-9.]+( deslop)/, `$1${version}$2`],
  ["docs/cli.md", /(npm install --global zero-slop@)[0-9.]+/, `$1${version}`],
  ["ONE-PAGER.md", /( · v)[0-9.]+( ·)/, `$1${version}$2`],
  ["mcp/README.md", /(exact Zero Slop )[0-9.]+/, `$1${version}`],
  ["mcp/gateway/wrangler.jsonc", /("SCORER_VERSION": ")[0-9.]+(")/, `$1${version}$2`],
  ["mcp/gateway/vitest.config.ts", /(scorerVersion: ")[0-9.]+(")/, `$1${version}$2`],
  ["website/app/page.tsx", /(skillVersion = ")[0-9.]+(")/, `$1${version}$2`],
  ["website/public/llms.txt", /(Current version: )[0-9.]+/, `$1${version}`],
  ["website/public/llms-full.txt", /(Current version: )[0-9.]+/, `$1${version}`],
];
// Multiple rules may target the same file. Stage every change before writing.
for (const [path, pattern, replacement] of rules) {
  const existing = changes.find((item) => item.path === path);
  const source = existing?.after ?? await read(path);
  if (!pattern.test(source)) throw new Error(`${path}: version marker changed; review before syncing`);
  const after = source.replace(pattern, replacement);
  if (after !== source) {
    if (existing) existing.after = after;
    else changes.push({ path, after });
  }
}
if (check && changes.length) {
  console.error(`Version ${version} differs in: ${changes.map((item) => item.path).join(", ")}`);
  process.exitCode = 1;
} else if (!check) {
  for (const { path, after } of changes) await writeFile(new URL(path, root), after);
  console.log(`Synchronized ${changes.length} version files to ${version}. Regenerate plugin, bundle, scorer and release ZIP, then run validation.`);
} else console.log(`Release version files agree on ${version}.`);
