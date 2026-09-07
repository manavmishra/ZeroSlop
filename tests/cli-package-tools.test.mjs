import assert from "node:assert/strict";
import test from "node:test";
import { mkdir, mkdtemp, realpath, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { npmCandidates, resolveNpmCommand, withPath } from "./helpers/npm-command.mjs";

test("Windows resolution handles node.exe, npm_execpath and quoted PATH entries without a shell", () => {
  const entries = npmCandidates({ platform: "win32", execPath: "C:\\Program Files\\nodejs\\node.exe",
    npmExecPath: "D:\\npm\\bin\\npm-cli.js", searchPath: '"E:\\Tools With Spaces";F:\\node;relative;;' });
  assert.equal(entries[0], "D:\\npm\\bin\\npm-cli.js");
  assert.ok(entries.includes("C:\\Program Files\\nodejs\\node_modules\\npm\\bin\\npm-cli.js"));
  assert.ok(entries.includes("E:\\Tools With Spaces\\node_modules\\npm\\bin\\npm-cli.js"));
  assert.ok(entries.includes("F:\\node\\node_modules\\npm\\bin\\npm-cli.js"));
  assert.equal(entries.some((entry) => /npm\.cmd$/.test(entry) || entry.includes("relative")), false);
});

test("POSIX resolution covers adjacent and lib npm layouts and ignores relative PATH entries", () => {
  const entries = npmCandidates({ platform: "linux", execPath: "/opt/node/bin/node", searchPath: "/usr/local/bin:relative::/usr/bin" });
  assert.ok(entries.includes("/opt/node/lib/node_modules/npm/bin/npm-cli.js"));
  assert.ok(entries.includes("/usr/local/bin/npm"));
  assert.equal(entries.some((entry) => entry.includes("relative")), false);
  assert.equal(new Set(entries).size, entries.length);
});

test("resolver validates npm package metadata and returns Node plus a literal entrypoint path", async (t) => {
  const directory = await mkdtemp(join(tmpdir(), "zero-slop-npm-resolution-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const npmRoot = join(directory, "node modules with spaces", "npm");
  const entry = join(npmRoot, "bin", "npm-cli.js");
  await mkdir(join(npmRoot, "bin"), { recursive: true });
  await writeFile(entry, "throw new Error('Resolution must not execute this fixture');\n");
  await writeFile(join(npmRoot, "package.json"), JSON.stringify({ name: "npm", bin: { npm: "bin/npm-cli.js" } }));
  const command = await resolveNpmCommand({ execPath: process.execPath, npmExecPath: entry, searchPath: "" });
  assert.equal(command.executable, process.execPath);
  assert.deepEqual(command.prefixArgs, [await realpath(entry)]);
  assert.equal(command.shell, false);
  // Remove access to real Node-adjacent npm to exercise the failure branch.
  await writeFile(join(npmRoot, "package.json"), JSON.stringify({ name: "unrelated", bin: { npm: "bin/npm-cli.js" } }));
  await assert.rejects(resolveNpmCommand({ execPath: join(directory, "absent", "node"), npmExecPath: entry, searchPath: "" }), /Could not resolve npm-cli\.js/);
});

test("no-Python environments remove every case variant of PATH", () => {
  assert.deepEqual(withPath({ Path: "python", PATH: "python", path: "python", SystemRoot: "C:\\Windows" }, ""), { SystemRoot: "C:\\Windows", PATH: "" });
});

test("real installed npm is resolved as a JavaScript file, never a shell command", async () => {
  const command = await resolveNpmCommand();
  assert.equal(command.executable, process.execPath);
  assert.equal(command.shell, false);
  assert.match(command.prefixArgs[0], /[\\/]npm-cli\.js$/);
});
