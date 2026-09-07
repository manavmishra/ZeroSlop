import { spawn } from "node:child_process";
import { join } from "node:path";

export const CLI_VERSION = "2.10.0";
export const MAX_LOCAL_BYTES = 100_000;
export const MAX_REMOTE_CHARS = 20_000;
const GENRES = new Set(["general", "social", "email", "research", "professional"]);

export function runtimeEnvironment(directory, env) {
  return {
    PATH: env.PATH, SYSTEMROOT: env.SYSTEMROOT,
    npm_config_cache: join(directory, "npm-cache"),
    npm_config_userconfig: join(directory, "user.npmrc"),
    npm_config_globalconfig: join(directory, "global.npmrc"),
    npm_config_registry: "https://registry.npmjs.org/",
    ZERO_SLOP_HOME: join(directory, "private"), ZERO_SLOP_NO_NOTES: "1", ZS_NO_UPDATE_CHECK: "1",
  };
}

export function command(executable, args, { cwd, env, input, timeoutMs = 30_000, maxBytes = 2_000_000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, { cwd, env, shell: false, stdio: ["pipe", "pipe", "pipe"] });
    const chunks = [];
    let bytes = 0;
    let finished = false;
    const fail = (error) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      child.kill("SIGKILL");
      reject(error);
    };
    const timer = setTimeout(() => fail(new Error("Command exceeded its time limit.")), timeoutMs);
    child.on("error", () => fail(new Error("Required command could not start.")));
    child.stdout.on("data", (chunk) => {
      bytes += chunk.length;
      if (bytes > maxBytes) fail(new Error("Command output exceeded its size limit."));
      else chunks.push(chunk);
    });
    // Scorer errors can contain source spans. Never print child stderr in CI.
    child.stderr.resume();
    child.stdin.on("error", () => undefined);
    child.on("close", (code, signal) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      if (signal) reject(new Error("Command was interrupted."));
      else {
        try {
          resolve({ code, stdout: new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)) });
        } catch {
          reject(new Error("Command output was not valid UTF-8."));
        }
      }
    });
    child.stdin.end(input);
  });
}

export function fullSha(value, name) {
  if (typeof value !== "string" || !/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/i.test(value) || /^0+$/.test(value)) {
    throw new Error(`${name} must be a full non-zero Git commit SHA.`);
  }
  return value;
}

export function optionsFromEnvironment(env, event) {
  const mode = env.INPUT_MODE || "score";
  if (!["score", "deslop"].includes(mode)) throw new Error("mode must be score or deslop.");
  if (env.GITHUB_EVENT_NAME === "pull_request_target") {
    throw new Error("Use pull_request, not the privileged pull_request_target event.");
  }
  const maxFiles = Number(env["INPUT_MAX-FILES"] || "10");
  if (!Number.isInteger(maxFiles) || maxFiles < 1 || maxFiles > 50) throw new Error("max-files must be an integer from 1 to 50.");
  const genre = env.INPUT_GENRE || "general";
  if (!GENRES.has(genre)) throw new Error("Unsupported genre.");
  const thresholdValue = env["INPUT_FAIL-ABOVE"]?.trim();
  const threshold = thresholdValue ? Number(thresholdValue) : null;
  if (threshold !== null && (!Number.isFinite(threshold) || threshold < 0 || threshold > 100)) {
    throw new Error("fail-above must be a number from 0 to 100.");
  }
  if (mode === "deslop" && threshold !== null) throw new Error("fail-above applies only to local score mode.");
  if (mode === "deslop" && event.pull_request && event.pull_request.head?.repo?.full_name !== env.GITHUB_REPOSITORY) {
    throw new Error("Hosted edits are disabled for fork pull requests. Use local score mode.");
  }
  return {
    mode, maxFiles, genre, threshold,
    base: fullSha(env["INPUT_BASE-SHA"] || event.pull_request?.base?.sha || event.before, "base-sha"),
    head: fullSha(env["INPUT_HEAD-SHA"] || event.pull_request?.head?.sha || env.GITHUB_SHA, "head-sha"),
  };
}

export function markdownFiles(output) {
  return [...new Set(output.split("\0").filter((name) => /\.(md|markdown)$/i.test(name)))];
}

export function safeLabel(value) {
  return value.replace(/[&<>|`\r\n\[\]\\]/g, (character) => `&#${character.charCodeAt(0)};`);
}

export function reportSummary(report) {
  const lines = [
    "## Zero Slop documentation review", "",
    report.mode === "score"
      ? "Local writing checks only. No draft was sent to a hosted editor. A score is not an authorship probability or a completed editorial review."
      : "Hosted editing was explicitly enabled. Review the returned edits before using them; no repository files were changed.",
    "", "| File | Writing score | Result |", "| --- | ---: | --- |",
  ];
  for (const item of report.files) {
    const scores = item.before === undefined ? "—" : item.after === undefined ? String(item.before) : `${item.before} → ${item.after}`;
    lines.push(`| ${safeLabel(item.file)} | ${scores} | ${safeLabel(item.status)} |`);
  }
  lines.push("", `${report.reviewed} reviewed; ${report.skipped} skipped. CLI ${CLI_VERSION}.`, "");
  return lines.join("\n");
}

export async function reviewFiles({ files, options, readBlob, runCli }) {
  const report = { schemaVersion: 1, cliVersion: CLI_VERSION, mode: options.mode, reviewed: 0, skipped: 0, thresholdFailed: false, errors: 0, files: [] };
  for (const [index, file] of files.entries()) {
    const skip = (status) => { report.skipped += 1; report.files.push({ file, status }); };
    if (index >= options.maxFiles) { skip("file limit"); continue; }
    const blob = await readBlob(file);
    if (!blob || !["100644", "100755"].includes(blob.mode)) { skip("not a regular tracked file"); continue; }
    if (blob.size > MAX_LOCAL_BYTES) { skip("file exceeds 100,000 bytes"); continue; }
    const text = blob.text;
    if (typeof text !== "string") { skip("file could not be read"); continue; }
    if (!text.trim()) { skip("empty file"); continue; }
    if (text.includes("\0")) { skip("binary content"); continue; }
    if (options.mode === "deslop" && [...text.trim()].length > MAX_REMOTE_CHARS) { skip("draft exceeds 20,000 Unicode code points"); continue; }
    try {
      const args = options.mode === "score"
        ? ["score", "-", "--", "--json", "--genre", options.genre, ...(["research", "professional"].includes(options.genre) ? ["--formal"] : [])]
        : ["deslop", "-", "--genre", options.genre, "--json"];
      const result = await runCli(args, text);
      if (result.code !== 0) throw new Error("Review command did not complete.");
      const payload = JSON.parse(result.stdout);
      if (options.mode === "score") {
        const score = payload.ai_likelihood;
        if (!Number.isFinite(score) || score < 0 || score > 100) throw new Error("Invalid writing report.");
        const above = options.threshold !== null && score > options.threshold;
        report.thresholdFailed ||= above;
        report.files.push({ file, before: score, status: above ? "above threshold" : "local check completed" });
      } else {
        if (typeof payload.text !== "string" || typeof payload.status !== "string" || !Number.isFinite(payload.before?.score) || !Number.isFinite(payload.after?.score)) {
          throw new Error("Invalid editing result.");
        }
        report.files.push({ file, before: payload.before.score, after: payload.after.score, status: payload.status, result: payload });
      }
      report.reviewed += 1;
    } catch {
      report.errors += 1;
      report.files.push({ file, status: "review unavailable" });
    }
  }
  return report;
}
