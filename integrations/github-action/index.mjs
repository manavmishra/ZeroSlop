import { appendFile, mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { CLI_VERSION, command, fullSha, markdownFiles, optionsFromEnvironment, reportSummary, reviewFiles, runtimeEnvironment } from "./review.mjs";

async function main() {
  const event = JSON.parse(await readFile(process.env.GITHUB_EVENT_PATH, "utf8"));
  const options = optionsFromEnvironment(process.env, event);
  const workspace = resolve(process.env.GITHUB_WORKSPACE || ".");
  const git = async (...args) => {
    const result = await command("git", ["--no-optional-locks", "--no-pager", "--literal-pathspecs", ...args], { cwd: workspace });
    if (result.code !== 0) throw new Error("Git comparison failed. Fetch both full commits before running this action.");
    return result.stdout;
  };
  const comparisonBase = event.pull_request
    ? fullSha((await git("merge-base", options.base, options.head)).trim(), "merge base")
    : options.base;
  const files = markdownFiles(await git("diff", "--no-renames", "--name-only", "-z", "--diff-filter=AM", comparisonBase, options.head, "--"));
  const directory = await mkdtemp(join(process.env.RUNNER_TEMP || tmpdir(), "zero-slop-review-"));
  const runtime = join(directory, "runtime");
  const cleanEnv = runtimeEnvironment(directory, process.env);
  await mkdir(runtime);
  await mkdir(cleanEnv.ZERO_SLOP_HOME);
  await writeFile(cleanEnv.npm_config_userconfig, "", { mode: 0o600 });
  await writeFile(cleanEnv.npm_config_globalconfig, "", { mode: 0o600 });
  // Ignore checkout-controlled npm configuration, lifecycle scripts and private
  // local preferences. Install the action's fixed release, never PR source code.
  if (files.length) {
    const install = await command(process.platform === "win32" ? "npm.cmd" : "npm", [
      "install", "--prefix", runtime, "--ignore-scripts", "--no-audit", "--no-fund", "--package-lock=false", `zero-slop@${CLI_VERSION}`,
    ], { cwd: directory, env: cleanEnv, timeoutMs: 120_000 });
    if (install.code !== 0) throw new Error(`Could not install zero-slop@${CLI_VERSION} from npm.`);
  }
  const cli = join(runtime, "node_modules", "zero-slop", "bin", "zero-slop.mjs");
  const report = await reviewFiles({
    files, options,
    readBlob: async (file) => {
      // Read Git blobs by object ID; symlinks, filters and working-tree paths
      // never run or redirect us outside the checked-out repository.
      const entry = (await git("ls-tree", "-z", options.head, "--", file)).split("\0")[0];
      const match = /^(\d+) blob ([a-f0-9]+)\t/.exec(entry);
      if (!match) return null;
      const [, mode, object] = match;
      const size = Number((await git("cat-file", "-s", object)).trim());
      if (!["100644", "100755"].includes(mode) || size > 100_000) return { mode, size };
      return { mode, size, text: await git("cat-file", "blob", object) };
    },
    runCli: (args, input) => command(process.execPath, [cli, ...args], {
      cwd: directory, env: cleanEnv, input, timeoutMs: options.mode === "deslop" ? 85_000 : 30_000,
    }),
  });
  const reportPath = join(directory, "review.json");
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, { mode: 0o600 });
  if (process.env.GITHUB_STEP_SUMMARY) await appendFile(process.env.GITHUB_STEP_SUMMARY, reportSummary(report));
  if (process.env.GITHUB_OUTPUT) {
    await appendFile(process.env.GITHUB_OUTPUT, `report-path=${reportPath}\nreviewed=${report.reviewed}\nskipped=${report.skipped}\n`);
  }
  console.log(`Zero Slop: ${report.reviewed} reviewed, ${report.skipped} skipped, ${report.errors} unavailable.`);
  if (report.errors || report.thresholdFailed) process.exitCode = 1;
}

main().catch((error) => {
  // Only locally authored errors reach this boundary; subprocess stderr and
  // source text are deliberately omitted from the job log.
  console.error(error instanceof SyntaxError ? "Invalid GitHub event data." : error.message);
  process.exitCode = 1;
});
