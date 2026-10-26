import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { access, mkdtemp, readFile, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { resolveNpmCommand } from "../../tests/helpers/npm-command.mjs";

const root = new URL("../../", import.meta.url);
const projects = ["website", "mcp/gateway", "mcp/scorer"];

test("every locked installer has an exact, explicit approval", async () => {
  for (const project of projects) {
    const manifest = JSON.parse(await readFile(new URL(`${project}/package.json`, root), "utf8"));
    const lock = JSON.parse(await readFile(new URL(`${project}/package-lock.json`, root), "utf8"));
    assert.ok(manifest.allowScripts, `${project} must declare reviewed installers`);
    const installers = new Set();
    for (const [path, entry] of Object.entries(lock.packages)) {
      if (!entry.hasInstallScript) continue;
      const name = path.split("node_modules/").at(-1);
      installers.add(`${name}@${entry.version}`);
      assert.equal(manifest.allowScripts[`${name}@${entry.version}`], true, `${project}: ${name}@${entry.version}`);
    }
    for (const [identity, approved] of Object.entries(manifest.allowScripts)) {
      assert.match(identity, /^(@[^/]+\/)?[^@]+@\d+\.\d+\.\d+$/);
      assert.equal(approved, true);
    }
    assert.deepEqual(new Set(Object.keys(manifest.allowScripts)), installers, `${project} must not carry unused approvals`);
  }
});

test("npm 11 strict install executes only explicitly approved dependencies", async () => {
  const npm = await resolveNpmCommand();
  const run = (arguments_, cwd) => spawnSync(npm.executable, [...npm.prefixArgs, ...arguments_], {
    cwd, encoding: "utf8", timeout: 60_000,
    env: { ...process.env, npm_config_audit: "false", npm_config_fund: "false" },
  });
  assert.match(run(["--version"], root).stdout.trim(), /^11\./, "this gate must use npm 11");
  const directory = await mkdtemp(join(tmpdir(), "zero-slop-script-policy-"));
  try {
    const dependency = join(directory, "dependency");
    await mkdir(dependency);
    await writeFile(join(dependency, "package.json"), JSON.stringify({
      name: "policy-test-installer", version: "1.0.0",
      scripts: { postinstall: "node -e \"require('node:fs').writeFileSync('installed-marker', 'ran')\"" },
    }));
    const packed = run(["pack", "--ignore-scripts", "--json", "--offline"], dependency);
    assert.equal(packed.status, 0, packed.stderr);
    const tarball = join(dependency, JSON.parse(packed.stdout)[0].filename);
    for (const [name, allowScripts, shouldPass] of [
      ["unreviewed", {}, false],
      // npm resolves file dependencies by exact source, not self-reported name.
      ["name-cannot-approve-tarball", { "policy-test-installer@1.0.0": true }, false],
      ["approved", { [`file:${tarball}`]: true }, true],
    ]) {
      const project = join(directory, name);
      await mkdir(project);
      await writeFile(join(project, "package.json"), JSON.stringify({
        name: `policy-test-${name}`, version: "1.0.0", private: true, allowScripts,
        dependencies: { "policy-test-installer": `file:${tarball}` },
      }));
      const installed = run([
        "install", "--offline", "--strict-allow-scripts", "--ignore-scripts=false",
        "--dangerously-allow-all-scripts=false", "--no-audit", "--no-fund",
      ], project);
      const marker = join(project, "node_modules/policy-test-installer/installed-marker");
      if (shouldPass) {
        assert.equal(installed.status, 0, installed.stderr);
        assert.equal(await readFile(marker, "utf8"), "ran");
      } else {
        assert.notEqual(installed.status, 0, `${name} must fail`);
        assert.match(installed.stderr, /allowScripts|allow.scripts|install.script/i);
        await assert.rejects(access(marker));
      }
    }
    const ordinary = join(directory, "ordinary");
    const plain = join(directory, "plain");
    await mkdir(plain);
    await writeFile(join(plain, "package.json"), JSON.stringify({ name: "policy-test-plain", version: "1.0.0" }));
    const plainPacked = run(["pack", "--ignore-scripts", "--json", "--offline"], plain);
    assert.equal(plainPacked.status, 0, plainPacked.stderr);
    await mkdir(ordinary);
    await writeFile(join(ordinary, "package.json"), JSON.stringify({
      name: "policy-test-ordinary", version: "1.0.0", private: true, allowScripts: {},
      dependencies: { "policy-test-plain": `file:${join(plain, JSON.parse(plainPacked.stdout)[0].filename)}` },
    }));
    const plainInstalled = run(["install", "--offline", "--strict-allow-scripts", "--no-audit", "--no-fund"], ordinary);
    assert.equal(plainInstalled.status, 0, plainInstalled.stderr);
    await access(join(ordinary, "node_modules/policy-test-plain/package.json"));
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
