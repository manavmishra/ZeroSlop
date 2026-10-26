import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const command = fileURLToPath(new URL('../bin/zero-slop.mjs', import.meta.url));
test('local clean-text CLI handles stdin without a model or upload', () => {
  const output = execFileSync(process.execPath, [command, 'clean-text', '-', '--json'], { input: 'The te\u200bxt is clear.', encoding: 'utf8' });
  const result = JSON.parse(output);
  assert.equal(result.text, 'The text is clear.');
  assert.equal(result.statisticalWatermark.status, 'not_verified');
});
test('local inspection and BOM preserve exact source text', () => {
  const source = '\ufeffThe te\u200bxt is clear.';
  const output = execFileSync(process.execPath, [command, 'clean-text', '-', '--inspect', '--json'], { input: source, encoding: 'utf8' });
  assert.equal(JSON.parse(output).text, source);
});
test('local cleanup rejects malformed UTF-8', () => {
  assert.throws(() => execFileSync(process.execPath, [command, 'clean-text', '-', '--json'], { input: Buffer.from([0xff]), stdio: ['pipe', 'pipe', 'pipe'] }));
});
