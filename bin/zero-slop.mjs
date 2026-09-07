#!/usr/bin/env node
// The npm package shipped four versions with no bin, no main and no scripts, so
// `npx zero-slop` did nothing and every real install went through the `skills`
// CLI against GitHub instead. That left the registry download count measuring
// mirrors rather than people. This is the executable half: it installs the same
// runtime the tarball already carries, and runs the scorer without a checkout.

import { cp, lstat, mkdir, open, readFile, readdir, rename, rm, stat } from "node:fs/promises";
import { constants } from "node:fs";
import { spawn } from "node:child_process";
import { homedir } from "node:os";
import { dirname, join, parse, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { deslop, DeslopError, isApprovedResult, validateInput } from "./lib/deslop.mjs";

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
  return `zero-slop ${v} — score locally or edit through the hosted Zero Slop MCP.

Usage
  npx zero-slop install [--harness <name>] [--dir <path>] [--force]
  npx zero-slop score <file|-> [-- <slopscore flags>]
  npx zero-slop deslop <file|-> [--genre <name>] [--audience <reader>] [--json]
                       [--require-approved] [--timeout <seconds>]
  npx zero-slop where
  npx zero-slop --version

Install targets
  --harness   ${Object.keys(HARNESS_DIRS).join(", ")}   (default: claude)
  --dir       install into an explicit directory instead
  --force     replace a verified Zero Slop installation

Hosted editing (deslop)
  Sends only the explicit draft, genre and audience to https://mcp.zero-slop.ai/mcp.
  Zero Slop does not store drafts or rewrites; aggregate usage metrics are recorded.
  Requires Node.js 22+, network access, and no Python or API key. No automatic retry.
  One UTF-8 file or stdin (-); 1–20,000 Unicode code points, audience at most 200.
  --genre     general (default), social, email, research, professional
  --json      full structured MCP result on stdout; notices stay on stderr
  --require-approved  exit 3 unless already clear or a checked rewrite; keep the result
  --timeout   whole remote request timeout in seconds (default: 75; maximum: 300)
  Text mode prints the returned draft on stdout and the review summary on stderr.
  No files are changed. A timeout or cancellation may not stop hosted processing.
  Exits: 0 valid result, 1 request failure, 2 invalid input, 3 approval gate,
         124 timeout, 130 interrupted, 143 terminated.

Examples
  npx zero-slop install                    # ~/.claude/skills/zero-slop
  npx zero-slop install --harness codex
  npx zero-slop score draft.md
  npx zero-slop score drafts/ -- --batch --gate 25
  npx zero-slop deslop draft.md --genre email
  npx zero-slop deslop - --json < draft.md

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
    child.on("close", (code, signal) => resolvePromise(code ?? (signal === "SIGINT" ? 130 : signal === "SIGTERM" ? 143 : 1)));
  });
}

function parseDeslopArgs(argv) {
  const values = {};
  const files = [];
  const allowedValues = new Set(["--genre", "--audience", "--timeout"]);
  let positionalOnly = false;
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (positionalOnly) { files.push(argument); continue; }
    if (argument === "--") { positionalOnly = true; continue; }
    const [flag, ...attached] = argument.split("=");
    if (allowedValues.has(flag)) {
      if (Object.hasOwn(values, flag)) throw new DeslopError("invalid_input", `Duplicate option: ${flag}`);
      const value = attached.length ? attached.join("=") : argv[++index];
      if (value === undefined || value.startsWith("--")) throw new DeslopError("invalid_input", `${flag} needs a value.`);
      values[flag] = value;
    } else if (argument === "--json" || argument === "--require-approved") {
      if (values[argument]) throw new DeslopError("invalid_input", `Duplicate option: ${argument}`);
      values[argument] = true;
    } else if (argument.startsWith("-") && argument !== "-") {
      throw new DeslopError("invalid_input", "Unknown deslop option. See: zero-slop deslop --help");
    } else files.push(argument);
  }
  if (files.length !== 1) throw new DeslopError("invalid_input", "deslop needs exactly one file or '-' for stdin; directories and batches are not uploaded.");
  const seconds = values["--timeout"] === undefined ? 75 : Number(values["--timeout"]);
  const timeoutMs = seconds * 1_000;
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 300_000) {
    throw new DeslopError("invalid_input", "--timeout needs 0.001–300 seconds.");
  }
  return { file: files[0], genre: values["--genre"], audience: values["--audience"],
    json: Boolean(values["--json"]), requireApproved: Boolean(values["--require-approved"]), timeoutMs };
}

async function readDraft(file, signal) {
  const maximum = 128 * 1024;
  let bytes;
  if (file === "-") {
    const chunks = [];
    let size = 0;
    const stop = () => process.stdin.destroy(signal.reason);
    signal.addEventListener("abort", stop, { once: true });
    try {
      signal.throwIfAborted();
      for await (const chunk of process.stdin) {
        signal.throwIfAborted();
        size += chunk.length;
        if (size > maximum) throw new DeslopError("invalid_input", "The input exceeds 128 KiB; nothing was uploaded.");
        chunks.push(chunk);
      }
      bytes = Buffer.concat(chunks);
    } finally { signal.removeEventListener("abort", stop); }
  } else {
    let handle;
    try {
      // Nonblocking open plus fstat rejects directories, devices and named pipes.
      handle = await open(file, constants.O_RDONLY | constants.O_NONBLOCK);
      const info = await handle.stat();
      if (!info.isFile() || info.size > maximum) throw new DeslopError("invalid_input", "Provide one regular UTF-8 file no larger than 128 KiB; nothing was uploaded.");
      // Keep the read bounded even if a regular file grows after fstat.
      const buffer = Buffer.alloc(maximum + 1);
      let size = 0;
      while (size < buffer.length) {
        signal.throwIfAborted();
        const { bytesRead } = await handle.read(buffer, size, buffer.length - size, null);
        if (!bytesRead) break;
        size += bytesRead;
      }
      if (size > maximum) throw new DeslopError("invalid_input", "The input exceeds 128 KiB; nothing was uploaded.");
      bytes = buffer.subarray(0, size);
    } finally { await handle?.close(); }
  }
  signal.throwIfAborted();
  try { return new TextDecoder("utf-8", { fatal: true }).decode(bytes); } catch {
    throw new DeslopError("invalid_input", "The draft must be valid UTF-8; nothing was uploaded.");
  }
}

async function runDeslop(argv, v) {
  const controller = new AbortController();
  let interrupted;
  let parsed;
  const json = argv.slice(0, argv.indexOf("--") < 0 ? undefined : argv.indexOf("--")).includes("--json");
  const stop = (signal) => {
    interrupted = signal;
    controller.abort(new DeslopError("cancelled", "Cancelled locally; hosted processing may still finish."));
  };
  const onInterrupt = () => stop("SIGINT");
  const onTerminate = () => stop("SIGTERM");
  process.once("SIGINT", onInterrupt);
  process.once("SIGTERM", onTerminate);
  try {
    parsed = parseDeslopArgs(argv);
    let text;
    try { text = await readDraft(parsed.file, controller.signal); } catch (error) {
      if (error instanceof DeslopError || controller.signal.aborted) throw error;
      throw new DeslopError("invalid_input", "The input file could not be read; nothing was uploaded.");
    }
    const input = validateInput({ text, genre: parsed.genre, audience: parsed.audience });
    console.error("Hosted editing: sending this draft to mcp.zero-slop.ai. Drafts and rewrites are not stored; aggregate usage metrics are recorded.");
    const result = await deslop(input, { signal: controller.signal, timeoutMs: parsed.timeoutMs,
      clientName: "zero-slop-cli", clientVersion: v });
    controller.signal.throwIfAborted();
    process.stdout.write(parsed.json ? `${JSON.stringify(result)}\n` : result.text);
    if (!parsed.json) {
      console.error(`Status: ${result.status}. Writing score: ${result.before.score} before, ${result.after.score} after. Lower is better.`);
      console.error(`Facts preserved: ${result.factsPreserved ? "yes" : "not confirmed"}. Final checks: ${result.passedFinalChecks ? "passed" : result.status === "already_clear" ? "not needed; already clear" : "did not all pass"}.`);
      // Notes can contain prose supplied by the service. Render them as text,
      // without allowing terminal-control sequences to execute.
      console.error(result.note.replace(/[\u0000-\u001f\u007f-\u009f]/g, " "));
    }
    return parsed.requireApproved && !isApprovedResult(result) ? 3 : 0;
  } catch (error) {
    const failure = controller.signal.aborted ? controller.signal.reason
      : error instanceof DeslopError ? error : new DeslopError("request_failed", "The request could not be completed.");
    const code = interrupted ? (interrupted === "SIGINT" ? 130 : 143)
      : failure.code === "timeout" ? 124 : failure.code === "invalid_input" ? 2 : 1;
    const details = { code: failure.code, message: failure.message,
      ...(failure.httpStatus !== undefined ? { httpStatus: failure.httpStatus } : {}),
      ...(failure.rpcCode !== undefined ? { rpcCode: failure.rpcCode } : {}),
      ...(failure.retryAfterSeconds !== undefined ? { retryAfterSeconds: failure.retryAfterSeconds } : {}) };
    if (json) process.stdout.write(`${JSON.stringify({ error: details })}\n`);
    console.error(failure.message);
    if (failure.retryAfterSeconds !== undefined) console.error(`Retry-After: ${failure.retryAfterSeconds} seconds. No retry was sent.`);
    return code;
  } finally {
    process.removeListener("SIGINT", onInterrupt);
    process.removeListener("SIGTERM", onTerminate);
  }
}

async function main() {
  const argv = process.argv.slice(2);
  // Parse this command separately: no install flags or scorer passthrough can
  // accidentally become a remote-upload option.
  if (argv[0] === "deslop") {
    const v = await version();
    if (argv.length === 2 && ["--help", "-h"].includes(argv[1])) { console.log(usage(v)); return 0; }
    return runDeslop(argv.slice(1), v);
  }
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
  .then((code) => { process.exitCode = code; })
  .catch((err) => {
    console.error(err.message);
    process.exitCode = 1;
  });
