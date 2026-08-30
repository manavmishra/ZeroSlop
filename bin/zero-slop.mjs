#!/usr/bin/env node
// The npm package shipped four versions with no bin, no main and no scripts, so
// `npx zero-slop` did nothing and every real install went through the `skills`
// CLI against GitHub instead. That left the registry download count measuring
// mirrors rather than people. This is the executable half: it installs the same
// runtime the tarball already carries, and runs the scorer without a checkout.

import { cp, mkdir, readFile, rm, stat } from "node:fs/promises";
import { spawn } from "node:child_process";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PAYLOAD = ["SKILL.md", "references", "scripts", "data"];

// Where each harness reads global skills from. `skills add` knows this mapping
// too; it is repeated here so the package works without that CLI installed.
const HARNESS_DIRS = {
  claude: ".claude/skills",
  codex: ".codex/skills",
  cursor: ".cursor/skills",
  opencode: ".config/opencode/skills",
  zed: ".config/zed/skills",
};

async function version() {
  const pkg = JSON.parse(await readFile(join(ROOT, "package.json"), "utf8"));
  return pkg.version;
}

function usage(v) {
  return `zero-slop ${v} — score AI-sounding prose 0-100 and edit it out.

Usage
  npx zero-slop install [--harness <name>] [--dir <path>] [--force]
  npx zero-slop score <file>... [-- <slopscore flags>]
  npx zero-slop where
  npx zero-slop --version

Install targets
  --harness   ${Object.keys(HARNESS_DIRS).join(", ")}   (default: claude)
  --dir       install into an explicit directory instead
  --force     overwrite an existing installation

Examples
  npx zero-slop install                    # ~/.claude/skills/zero-slop
  npx zero-slop install --harness codex
  npx zero-slop score draft.md
  npx zero-slop score drafts/ -- --batch --gate 25

Docs: https://zero-slop.ai   Source: https://github.com/manavmishra/ZeroSlop`;
}

function parseArgs(argv) {
  const flags = {};
  const rest = [];
  let passthrough = [];
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--") {
      passthrough = argv.slice(i + 1);
      break;
    }
    if (a === "--force") flags.force = true;
    else if (a === "--harness" || a === "--dir") flags[a.slice(2)] = argv[++i];
    else if (a.startsWith("--harness=")) flags.harness = a.split("=")[1];
    else if (a.startsWith("--dir=")) flags.dir = a.split("=")[1];
    else rest.push(a);
  }
  return { flags, rest, passthrough };
}

function targetDir(flags) {
  if (flags.dir) return resolve(flags.dir);
  const harness = flags.harness ?? "claude";
  const base = HARNESS_DIRS[harness];
  if (!base) {
    throw new Error(
      `unknown harness "${harness}". Known: ${Object.keys(HARNESS_DIRS).join(", ")}`,
    );
  }
  return join(homedir(), base, "zero-slop");
}

async function exists(p) {
  try {
    await stat(p);
    return true;
  } catch {
    return false;
  }
}

async function install(flags) {
  const dest = targetDir(flags);
  if ((await exists(dest)) && !flags.force) {
    console.error(
      `zero-slop is already installed at ${dest}\n` +
        `Re-run with --force to overwrite it, or --dir to install elsewhere.`,
    );
    return 1;
  }
  // Replace rather than merge: a stale reference file left behind by an older
  // version is a silent behaviour change, which is the failure this avoids.
  await rm(dest, { recursive: true, force: true });
  await mkdir(dest, { recursive: true });
  for (const entry of PAYLOAD) {
    await cp(join(ROOT, entry), join(dest, entry), { recursive: true });
  }
  console.log(`Installed zero-slop ${await version()} into ${dest}`);
  console.log("Restart your agent, then run: /zero-slop (your writing)");
  return 0;
}

function runScorer(args) {
  return new Promise((resolvePromise) => {
    const script = join(ROOT, "scripts", "slopscore.py");
    const child = spawn("python3", [script, ...args], { stdio: "inherit" });
    child.on("error", (err) => {
      if (err.code === "ENOENT") {
        console.error(
          "python3 was not found on PATH. The scorer is a standard-library " +
            "Python program and needs Python 3 to run.",
        );
        resolvePromise(127);
        return;
      }
      console.error(err.message);
      resolvePromise(1);
    });
    child.on("close", (code) => resolvePromise(code ?? 0));
  });
}

async function main() {
  const argv = process.argv.slice(2);
  const { flags, rest, passthrough } = parseArgs(argv);
  const command = rest[0];
  const v = await version();

  if (argv.includes("--version") || argv.includes("-v")) {
    console.log(v);
    return 0;
  }
  if (!command || argv.includes("--help") || argv.includes("-h") || command === "help") {
    console.log(usage(v));
    return command || argv.length ? 0 : 0;
  }
  if (command === "install") return install(flags);
  if (command === "where") {
    console.log(targetDir(flags));
    return 0;
  }
  if (command === "score") {
    const files = rest.slice(1);
    if (!files.length && !passthrough.length) {
      console.error("score needs at least one file. See: npx zero-slop --help");
      return 2;
    }
    return runScorer([...files, ...passthrough]);
  }

  console.error(`unknown command "${command}". See: npx zero-slop --help`);
  return 2;
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    console.error(err.message);
    process.exit(1);
  });
