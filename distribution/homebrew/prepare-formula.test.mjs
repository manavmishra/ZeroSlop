import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { METADATA_URL, TARBALL_URL, VERSION, prepareFormula } from "./prepare-formula.mjs";

const fixture = Buffer.from("unit-test archive bytes, never a published release");
const metadata = {
  name: "zero-slop", version: VERSION,
  dist: {
    tarball: TARBALL_URL,
    integrity: `sha512-${createHash("sha512").update(fixture).digest("base64")}`,
  },
};

async function temporaryOutput(t) {
  const dir = await mkdtemp(join(tmpdir(), "zero-slop-homebrew-test-"));
  t.after(() => rm(dir, { recursive: true, force: true }));
  return join(dir, "Formula", "zero-slop.rb");
}

function releaseFetch(value = metadata, bytes = fixture, status = 200) {
  return async (url, options) => {
    assert.equal(options.redirect, "error");
    assert.ok(options.signal instanceof AbortSignal);
    if (url === METADATA_URL) return new Response(JSON.stringify(value), { status });
    assert.equal(url, TARBALL_URL);
    return new Response(bytes);
  };
}

test("renders exact version and SHA-256 only after validating published integrity", async (t) => {
  const output = await temporaryOutput(t);
  const report = await prepareFormula(output, releaseFetch());
  const formula = await readFile(output, "utf8");
  const expected = createHash("sha256").update(fixture).digest("hex");
  assert.equal(report.sha256, expected);
  assert.match(formula, new RegExp(`sha256 "${expected}"`));
  assert.ok(formula.includes(`url "${TARBALL_URL}"`));
  assert.ok(!formula.includes("__NPM_TARBALL_SHA256__"));
  assert.ok(!formula.includes("sha256 :no_check"));
  assert.ok(formula.includes('depends_on "node"'));
  assert.ok(formula.includes('depends_on "python@3.14"'));
  assert.ok(formula.includes('system "npm", "install", *std_npm_args'));
  assert.ok(!formula.includes("ignore_scripts: false"));
  assert.ok(formula.includes('result.fetch("score_kind")'));
  assert.ok(formula.includes('"install", "--dir", testpath/"installed-skill"'));
});

for (const [name, value, bytes, status, message] of [
  ["unpublished release", {}, fixture, 404, /metadata unavailable/],
  ["wrong version", { ...metadata, version: "2.9.2" }, fixture, 200, /exact zero-slop/],
  ["wrong package", { ...metadata, name: "other" }, fixture, 200, /exact zero-slop/],
  ["different tarball host", { ...metadata, dist: { ...metadata.dist, tarball: "https://example.com/file.tgz" } }, fixture, 200, /exact zero-slop/],
  ["missing integrity", { ...metadata, dist: { tarball: TARBALL_URL } }, fixture, 200, /SHA-512/],
  ["tampered bytes", metadata, Buffer.from("tampered"), 200, /does not match/],
]) {
  test(`refuses ${name} without writing a formula`, async (t) => {
    const output = await temporaryOutput(t);
    await assert.rejects(prepareFormula(output, releaseFetch(value, bytes, status)), message);
    await assert.rejects(stat(output), { code: "ENOENT" });
  });
}

test("does not overwrite a reviewed formula", async (t) => {
  const output = await temporaryOutput(t);
  await prepareFormula(output, releaseFetch());
  await writeFile(output, "reviewed formula\n");
  await assert.rejects(prepareFormula(output, releaseFetch()), { code: "EEXIST" });
  assert.equal(await readFile(output, "utf8"), "reviewed formula\n");
});
