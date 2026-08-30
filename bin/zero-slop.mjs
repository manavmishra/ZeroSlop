#!/usr/bin/env node
// The npm package shipped four versions with no bin, no main and no scripts, so
// `npx zero-slop` did nothing and every real install went through the `skills`
// CLI against GitHub instead. That left the registry download count measuring
// mirrors rather than people. This is the executable half: it installs the same
// runtime the tarball already carries, and runs the scorer without a checkout.

import { cp, lstat, mkdir, readFile, readdir, rename, rm, stat } from "node:fs/promises";
import { spawn } from "node:child_process";
import { homedir } from "node:os";
import { dirname, join, parse, resolve } from "node:path";
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
  --force     replace a verified Zero Slop installation

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
    else if (a === "--harness" || a === "--dir") {
      const value = argv[i + 1];
      if (!value || value.startsWith("--")) throw new Error(`${a} needs a value`);
      flags[a.slice(2)] = value;
      i += 1;
    } else if (a.startsWith("--harness=")) {
      flags.harness = a.slice("--harness=".length);
      if (!flags.harness) throw new Error("--harness needs a value");
    } else if (a.startsWith("--dir=")) {
      flags.dir = a.slice("--dir=".length);
      if (!flags.dir) throw new Error("--dir needs a value");
    } else rest.push(a);
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

function assertNarrowTarget(dest) {
  const target = resolve(dest);
  const forbidden = new Set([
    parse(target).root,
    resolve(homedir()),
    resolve(process.cwd()),
    ROOT,
  ]);
  if (forbidden.has(target)) {
    throw new Error(`refusing broad install target: ${target}`);
  }
}

async function verifiedExistingInstall(dest) {
  const info = await lstat(dest);
  if (info.isSymbolicLink() || !info.isDirectory()) return false;
  const entries = await readdir(dest);
  if (!entries.length) return true;
  try {
    const skill = await readFile(join(dest, "SKILL.md"), "utf8");
    const header = skill.split("---", 3)[1] ?? "";
    const runtime = await lstat(join(dest, "scripts", "slopscore.py"));
    const patterns = await lstat(join(dest, "data", "patterns.json"));
    return /^name:\s*zero-slop\s*$/m.test(header)
      && runtime.isFile() && patterns.isFile();
  } catch {
    return false;
  }
}

async function install(flags) {
  const dest = targetDir(flags);
  assertNarrowTarget(dest);
  const present = await exists(dest);
  if (present && !flags.force) {
    console.error(
      `zero-slop is already installed at ${dest}\n` +
        `Re-run with --force to overwrite it, or --dir to install elsewhere.`,
    );
    return 1;
  }
  if (present && !(await verifiedExistingInstall(dest))) {
    throw new Error(
      `refusing to overwrite ${dest}: it is not a Zero Slop installation`,
    );
  }

  // Build the complete payload beside the destination before replacing an
  // existing install. A copy failure therefore leaves the working version
  // untouched, and the backup is restored if the final rename fails.
  const nonce = `${process.pid}-${Date.now()}`;
  const staged = `${dest}.installing-${nonce}`;
  const backup = `${dest}.backup-${nonce}`;
  await mkdir(dirname(dest), { recursive: true });
  await mkdir(staged);
  try {
    for (const entry of PAYLOAD) {
      await cp(join(ROOT, entry), join(staged, entry), { recursive: true });
    }
    if (present) await rename(dest, backup);
    try {
      await rename(staged, dest);
    } catch (exc) {
      if (present && (await exists(backup)) && !(await exists(dest))) {
        await rename(backup, dest);
      }
      throw exc;
    }
    if (present) await rm(backup, { recursive: true, force: true });
  } finally {
    await rm(staged, { recursive: true, force: true });
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
  if (command === "install") {
    if (rest.length !== 1 || passthrough.length) {
      console.error("install accepts only --harness, --dir, and --force");
      return 2;
    }
    return install(flags);
  }
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
