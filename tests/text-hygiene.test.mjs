import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { cleanTextHygiene, inspectTextHygiene, reverseTextHygiene, createTextHygiene } from '../bin/lib/text-hygiene.mjs';

const fixtures = JSON.parse(await readFile(new URL('./fixtures/text-hygiene.json', import.meta.url), 'utf8'));
for (const fixture of fixtures) {
  test(`text hygiene: ${fixture.name}`, () => {
    const result = cleanTextHygiene(fixture.input);
    assert.equal(result.text, fixture.expected);
    assert.equal(result.offsetUnit, 'utf16');
    assert.equal(cleanTextHygiene(result.text).text, result.text);
    assert.equal(reverseTextHygiene(result.text, result.edits), fixture.input);
    assert.equal(result.statisticalWatermark.status, 'not_verified');
    assert.equal(result.status, result.edits.length ? 'cleaned' : 'unchanged');
    assert.deepEqual(createTextHygiene().cleanTextHygiene(fixture.input), result);
  });
}
test('inspection never attributes a platform or claims statistical removal', () => {
  const result = inspectTextHygiene('The te\u200bxt is clear.');
  assert.equal(result.findings.length, 1);
  assert.equal(result.findings[0].codePoint, 'U+200B');
  assert.equal(result.statisticalWatermark.status, 'not_verified');
  assert.equal('platform' in result, false);
});
test('undo rejects stale content and malformed edits', () => {
  const result = cleanTextHygiene('The te\u200bxt is clear.');
  assert.throws(() => reverseTextHygiene(result.text + ' changed', result.edits));
  assert.throws(() => reverseTextHygiene(result.text, [{ start: -1 }]));
  assert.throws(() => reverseTextHygiene(result.text, [null]));
  assert.throws(() => reverseTextHygiene(result.text, [{ ...result.edits[0], start: 999999 }]));
  for (const edit of [null, [], 'edit',
    { ...result.edits[0], start: true, end: 2, outputStart: true },
    { ...result.edits[0], start: 0, end: 1, outputStart: 0 },
    { ...result.edits[0], start: -1, end: 0, outputStart: -1 },
    { ...result.edits[0], start: 1.5, end: 2.5, outputStart: 1.5 },
    { ...result.edits[0], outputStart: -1 },
    { ...result.edits[0], outputStart: result.text.length + 1 },
    { ...result.edits[0], outputBinding: 'mismatched' }]) {
    assert.throws(() => reverseTextHygiene(result.text, [edit]));
  }
});
test('dense supported artifacts remain bounded and reverse exactly', () => {
  const text = 'The te\u200bxt is clear.\n'.repeat(9000);
  const started = performance.now();
  const result = cleanTextHygiene(text);
  assert.equal(result.edits.length, 9000);
  assert.equal(reverseTextHygiene(result.text, result.edits), text);
  assert.ok(performance.now() - started < 5000);
});
test('invalid and over-limit inputs fail before transformation', () => {
  assert.throws(() => cleanTextHygiene(null), TypeError);
  assert.throws(() => cleanTextHygiene('x'.repeat(200001)), RangeError);
});
