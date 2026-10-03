import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import test, { after } from "node:test";

const require = createRequire(import.meta.url);
const adapter = require("../compat/glob/index.js");
const fixture = mkdtempSync(path.join(tmpdir(), "zero-slop-glob-"));
after(() => rmSync(fixture, { recursive: true, force: true }));
for (const directory of ["modules/nested", "projects/site-a", "projects/site-b", "empty", "app"]) {
  mkdirSync(path.join(fixture, directory), { recursive: true });
}
for (const filename of [
  "modules/a.js", "modules/b.ts", "modules/nested/c.js", "modules/.hidden.js",
  "modules/readme.md", "projects/file.txt", "app/page.tsx", "importer.ts",
]) {
  writeFileSync(path.join(fixture, filename), "export default 1;\n");
}
symlinkSync("modules", path.join(fixture, "linked-modules"), "dir");
const sorted = (values) => [...values].sort();
const options = { cwd: fixture };

test("only the two pinned synchronous interfaces are exposed", () => {
  assert.deepEqual(Object.keys(adapter).sort(), ["__esModule", "default", "globSync", "sync"]);
  assert.equal(adapter.globSync, adapter.sync);
  assert.equal(typeof adapter, "object");
});

test("native ESM and synchronous CommonJS loading expose the same functions", async () => {
  const esm = await import("../compat/glob/index.js");
  assert.deepEqual(Object.keys(esm).sort(), ["default", "globSync", "sync"]);
  assert.equal(esm.sync, adapter.sync);
  assert.equal(esm.globSync, adapter.globSync);
  assert.deepEqual(Object.keys(esm.default).sort(), ["globSync", "sync"]);
  assert.equal(esm.default.sync, adapter.sync);
  assert.equal(esm.default.globSync, adapter.globSync);
});

test("extension braces, recursive discovery and duplicate patterns preserve file sets", () => {
  const expected = ["modules/a.js", "modules/b.ts", "modules/nested/c.js"];
  assert.deepEqual(sorted(adapter.sync("modules/**/*.{js,ts}", options)), expected);
  assert.deepEqual(sorted(adapter.sync(["modules/**/*.js", "modules/**/*.{js,ts}"], options)), expected);
});

test("negation, extglobs and character classes retain selection semantics", () => {
  assert.deepEqual(adapter.sync(["modules/**/*.{js,ts}", "!modules/nested/**"], options).sort(), ["modules/a.js", "modules/b.ts"]);
  assert.deepEqual(adapter.sync("modules/@(a|b).{js,ts}", options).sort(), ["modules/a.js", "modules/b.ts"]);
  assert.deepEqual(adapter.sync("modules/[ab].{js,ts}", options).sort(), ["modules/a.js", "modules/b.ts"]);
});

test("directory mode does not include files or automatically expand directory arguments", () => {
  assert.deepEqual(adapter.globSync("projects/*", { ...options, onlyDirectories: true }).sort(), ["projects/site-a", "projects/site-b"]);
  assert.deepEqual(adapter.sync("modules", options), []);
  assert.deepEqual(adapter.globSync("empty", { ...options, onlyDirectories: true }), ["empty"]);
  assert.deepEqual(adapter.globSync("empty", options), []);
});

test("relative cwd, absolute patterns and empty patterns/results are handled", () => {
  assert.deepEqual(adapter.sync("*.js", { cwd: path.join(fixture, "modules") }), ["a.js"]);
  assert.deepEqual(adapter.sync(path.join(fixture, "modules", "a.js")), [path.join(fixture, "modules", "a.js")]);
  assert.deepEqual(adapter.sync([], options), []);
  assert.deepEqual(adapter.sync("missing/**/*", options), []);
});

test("hidden files are excluded by default and existing symlink traversal remains active", () => {
  assert.equal(adapter.sync("modules/**/*.js", options).includes("modules/.hidden.js"), false);
  assert.deepEqual(adapter.sync("linked-modules/**/*.js", options).sort(), ["linked-modules/a.js", "linked-modules/nested/c.js"]);
});

test("unsupported APIs and options cannot silently weaken consumers", () => {
  for (const key of ["deep", "fs", "dot", "ignore", "absolute", "expandDirectories", "onlyFiles", "objectMode"]) {
    assert.throws(() => adapter.sync("*", { [key]: true }), /Unsupported website glob option/);
  }
  assert.throws(() => adapter.sync("*", { [Symbol("extra")]: true }), /Unsupported website glob option/);
  for (const value of [null, [], 1, "options"]) {
    assert.throws(() => adapter.sync("*", value), /Glob options must be an object/);
  }
  assert.throws(() => adapter.sync("*", { cwd: 1 }), /cwd must be a string/);
  assert.throws(() => adapter.sync("*", { onlyDirectories: "true" }), /must be a boolean/);
  assert.throws(() => adapter.sync([path.join(fixture, "modules/*.js"), "modules/*.js"], options), /Mixed absolute and relative/);
  for (const patterns of [null, undefined, "", ["*.js", 1]]) {
    assert.throws(() => adapter.sync(patterns, options), /nonempty string/);
  }
});

test("adversarial depth and length are rejected before matching", () => {
  for (const [open, close] of [["{", "}"], ["(", ")"]]) {
    assert.doesNotThrow(() => adapter.sync(open.repeat(100) + "a,b" + close.repeat(100), options));
    assert.throws(() => adapter.sync(open.repeat(101) + "a,b" + close.repeat(101), options), /100-level/);
    assert.throws(() => adapter.sync(open.repeat(4000) + "a,b" + close.repeat(4000), options), /100-level/);
  }
  assert.doesNotThrow(() => adapter.sync("a".repeat(10000), options));
  assert.throws(() => adapter.sync("a".repeat(10001), options), /10000-character/);
  assert.doesNotThrow(() => adapter.sync("\\{".repeat(101), options));
  assert.doesNotThrow(() => adapter.sync("[{]".repeat(101), options));
});

test("both actual consumer dependency paths resolve to the new implementation", () => {
  for (const consumer of ["@next/eslint-plugin-next", "vite-plugin-dynamic-import"]) {
    const consumerRequire = createRequire(require.resolve(consumer));
    const installedPath = consumerRequire.resolve("fast-glob");
    assert.equal(consumerRequire("fast-glob"), adapter);
    const manifest = JSON.parse(readFileSync(path.join(path.dirname(installedPath), "package.json"), "utf8"));
    assert.equal(manifest.name, "@zero-slop/website-glob-compat");
    assert.deepEqual(manifest.dependencies, { tinyglobby: "0.2.17" });
  }
});

test("actual Next root-directory discovery handles globs, arrays and normalized Windows separators", () => {
  const nextEntry = require.resolve("@next/eslint-plugin-next");
  const { getRootDirs } = require(path.join(path.dirname(nextEntry), "utils/get-root-dirs.js"));
  const pattern = path.join(fixture, "projects", "*");
  const expected = [path.join(fixture, "projects/site-a"), path.join(fixture, "projects/site-b")];
  for (const rootDir of [pattern, pattern.replaceAll("/", "\\"), [pattern, 1]]) {
    assert.deepEqual(getRootDirs({ cwd: fixture, settings: { next: { rootDir } } }).sort(), expected);
  }
  assert.deepEqual(getRootDirs({ cwd: fixture, settings: {} }), [fixture]);
});

test("actual dynamic-import CJS and ESM consumers retain extension discovery", async () => {
  const cjsPath = require.resolve("vite-plugin-dynamic-import");
  const variants = [require(cjsPath), await import(pathToFileURL(path.join(path.dirname(cjsPath), "index.mjs")).href)];
  const { parseExpressionAt } = require("acorn");
  const expression = "`./modules/${name}`";
  for (const consumer of variants) {
    const result = await consumer.globFiles({
      importeeNode: parseExpressionAt(expression, 0, { ecmaVersion: "latest" }),
      importExpression: `import(${expression})`,
      importer: path.join(fixture, "importer.ts"),
      resolve: { tryResolve: async () => undefined },
      extensions: [".js", ".ts"],
      loose: false,
    });
    assert.deepEqual(result.files.sort(), ["./modules/a.js", "./modules/b.ts"]);
  }
});

test("locked graph contains no vulnerable glob code and keeps the pinned tooling", () => {
  const lock = JSON.parse(readFileSync(new URL("../package-lock.json", import.meta.url), "utf8"));
  for (const [location, manifest] of Object.entries(lock.packages)) {
    assert.equal(/node_modules\/(?:braces|micromatch)$/.test(location), false, location);
    assert.equal(Object.hasOwn(manifest.dependencies ?? {}, "braces"), false, location);
    assert.equal(Object.hasOwn(manifest.dependencies ?? {}, "micromatch"), false, location);
    if (/node_modules\/fast-glob$/.test(location)) {
      assert.equal(manifest.resolved, "compat/glob");
      assert.equal(manifest.link, true);
    }
  }
  for (const [name, version] of [
    ["@next/eslint-plugin-next", "16.2.6"], ["vinext", "1.0.0-beta.8"],
    ["vite-plugin-commonjs", "0.10.4"], ["vite-plugin-dynamic-import", "1.6.0"],
  ]) assert.equal(lock.packages[`node_modules/${name}`].version, version);
  assert.equal(lock.packages["compat/glob"].name, "@zero-slop/website-glob-compat");
  assert.equal(lock.packages["compat/glob"].extraneous, undefined);
  const manifest = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
  assert.equal(manifest.devDependencies["fast-glob"], "file:compat/glob");
  assert.equal(manifest.overrides["fast-glob"], "$fast-glob");
});
