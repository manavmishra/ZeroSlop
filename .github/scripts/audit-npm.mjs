#!/usr/bin/env node

import { spawn } from "node:child_process";
import { pathToFileURL } from "node:url";

const TRANSIENT = /(?:\b(?:408|429|500|502|503|504)\b|ECONNRESET|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN|ENETUNREACH|socket hang up|service unavailable|audit endpoint returned an error|request timed out)/i;
const RETIRED_QUICK_ENDPOINT = /This endpoint is being retired[\s\S]*Invalid package tree/i;

export function classifyAuditFailure(output) {
  const value = String(output || "");
  if (/"auditReportVersion"\s*:\s*\d+/i.test(value)
      && /"vulnerabilities"\s*:\s*\{/i.test(value)) {
    return "findings";
  }
  if (TRANSIENT.test(value) || RETIRED_QUICK_ENDPOINT.test(value)) return "retry";
  return "fatal";
}

export function allowsUnavailableAudit(value) {
  return /^(?:1|true)$/i.test(String(value || "").trim());
}

function positiveInteger(value, fallback) {
  const parsed = Number.parseInt(value || "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function run(command, args, timeoutMs) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGTERM");
      setTimeout(() => child.kill("SIGKILL"), 5_000).unref();
    }, timeoutMs);
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (error) => {
      clearTimeout(timer);
      resolve({ code: null, stdout, stderr: `${stderr}\n${error.stack || error}`, timedOut });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr, timedOut });
    });
  });
}

async function main() {
  const attempts = positiveInteger(process.env.AUDIT_MAX_ATTEMPTS, 3);
  const timeoutMs = positiveInteger(process.env.AUDIT_ATTEMPT_TIMEOUT_MS, 75_000);
  const baseDelayMs = positiveInteger(process.env.AUDIT_RETRY_DELAY_MS, 5_000);
  const fetchTimeoutMs = Math.max(10_000, Math.min(60_000, timeoutMs - 10_000));

  // npm ci should leave an exact tree. Prove that locally before treating the
  // registry's retired quick-endpoint "invalid tree" response as retryable.
  const tree = await run("npm", ["ls", "--all", "--json"], 45_000);
  if (tree.code !== 0) {
    process.stderr.write(`${tree.stdout}\n${tree.stderr}`.trim() + "\n");
    process.stderr.write("The installed dependency tree is invalid; refusing to audit it.\n");
    process.exitCode = 1;
    return;
  }

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    process.stderr.write(`Dependency audit ${attempt}/${attempts}...\n`);
    const result = await run("npm", [
      "audit",
      "--audit-level=high",
      "--json",
      `--fetch-timeout=${fetchTimeoutMs}`,
      "--fetch-retries=0",
    ], timeoutMs);
    if (result.code === 0) {
      process.stdout.write("Dependency audit passed.\n");
      return;
    }

    const output = `${result.stdout}\n${result.stderr}${result.timedOut ? "\nrequest timed out" : ""}`;
    const classification = classifyAuditFailure(output);
    if (classification !== "retry" || attempt === attempts) {
      process.stderr.write(output.trim() + "\n");
      if (classification === "findings") {
        process.stderr.write("The audit completed and found a high-severity dependency vulnerability.\n");
      } else if (classification === "retry") {
        const unavailableMessage = "The registry remained unavailable after every bounded retry.";
        process.stderr.write(`${unavailableMessage}\n`);
        // Validation still runs the deterministic tests when npm's optional
        // advisory service is down. Releases do not set this opt-in and remain
        // fail-closed. A real audit report with findings always fails above.
        if (allowsUnavailableAudit(process.env.AUDIT_ALLOW_UNAVAILABLE)) {
          process.stdout.write(`::warning title=Dependency audit unavailable::${unavailableMessage} No vulnerability result was recorded; deterministic checks will continue.\n`);
          return;
        }
      } else {
        process.stderr.write("The audit failed for a non-transient reason.\n");
      }
      process.exitCode = 1;
      return;
    }

    const delayMs = baseDelayMs * attempt;
    process.stderr.write(`The npm audit service is temporarily unavailable; retrying in ${Math.round(delayMs / 1_000)}s.\n`);
    await wait(delayMs);
  }
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invokedDirectly) await main();
