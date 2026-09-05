#!/usr/bin/env node
// Build-only checks for the silent studio film. These measure timing and
// continuity, not production taste; the encoded movie still needs visual QA.
//
// node growth/check-studio-cadence.mjs
// node growth/check-studio-cadence.mjs --manifest /tmp/frames/manifest.json \
//   --inspections /tmp/frames/motion-inspections.json
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import * as studio from './studio-timeline.mjs';

const EPSILON = 1e-6;
const EXPECTED_DURATION = 24000;
const EXPECTED_FPS = 30;
const FRAME_MS = 1000 / EXPECTED_FPS;
const EXPECTED_FRAMES = EXPECTED_DURATION * EXPECTED_FPS / 1000;

const close = (actual, expected, message, tolerance = EPSILON) => {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance,
    `${message}: expected ${expected}, received ${actual}`);
};
const options = new Map();
const args = process.argv.slice(2);
if (args.length === 1 && args[0] === '--help') {
  console.log('Usage: node growth/check-studio-cadence.mjs [--manifest FILE.json] [--inspections FILE.json]');
  process.exit(0);
}
assert.equal(args.length % 2, 0, 'Each option needs a path.');
for (let i = 0; i < args.length; i += 2) {
  assert.ok(['--manifest', '--inspections'].includes(args[i]), `Unknown option: ${args[i]}`);
  assert.ok(!options.has(args[i]), `Repeated option: ${args[i]}`);
  options.set(args[i], args[i + 1]);
}

function checkUniformFrames(entries, label) {
  assert.ok(Array.isArray(entries), `${label} must be an array.`);
  assert.equal(entries.length, EXPECTED_FRAMES, `${label} must have one entry per output frame.`);
  let elapsed = 0;
  for (const [index, entry] of entries.entries()) {
    close(elapsed, index * FRAME_MS, `${label} frame ${index} starts on the output grid`);
    if ('t' in entry) close(entry.t, index * FRAME_MS, `${label} frame ${index} sample time`);
    close(entry.durationMs, FRAME_MS, `${label} frame ${index} duration`);
    const encodedStart = Math.round(elapsed * EXPECTED_FPS / 1000);
    elapsed += entry.durationMs;
    const encodedEnd = Math.round(elapsed * EXPECTED_FPS / 1000);
    assert.equal(encodedEnd - encodedStart, 1,
      `${label} frame ${index} would be dropped or repeated by the native encoder.`);
  }
  close(elapsed, EXPECTED_DURATION, `${label} total duration`);
}

// No time fields: their expected linear progression is not a scene transform.
function numericState(value, prefix = '', result = {}) {
  if (typeof value === 'number') {
    assert.ok(Number.isFinite(value), `Non-finite motion value: ${prefix}`);
    if (!/(^|\.)(t|time|timeMs|presentationTime|sourceTime)$/.test(prefix)) result[prefix] = value;
  } else if (Array.isArray(value)) {
    value.forEach((item, index) => numericState(item, `${prefix}.${index}`, result));
  } else if (value && typeof value === 'object') {
    for (const [key, item] of Object.entries(value)) {
      numericState(item, prefix ? `${prefix}.${key}` : key, result);
    }
  }
  return result;
}

function checkMotion() {
  assert.equal(typeof studio.studioMotion, 'function', 'studioMotion must expose pure presentation-time state.');
  const samples = Array.from({length: EXPECTED_DURATION + 1}, (_, t) => numericState(studio.studioMotion(t)));
  const keys = Object.keys(samples[0]);
  assert.ok(keys.length >= 3, 'Motion state must expose numeric transforms and opacity.');
  for (const required of ['logo.opacity', 'housing.opacity', 'camera.z']) {
    assert.ok(keys.includes(required), `Motion state is missing ${required}.`);
  }
  for (const [t, sample] of samples.entries()) {
    assert.deepEqual(Object.keys(sample), keys, `Motion schema changes at ${t} ms.`);
    for (const key of keys.filter(key => /opacity/i.test(key))) {
      assert.ok(sample[key] >= -EPSILON && sample[key] <= 1 + EPSILON,
        `${key} leaves the opacity range at ${t} ms.`);
    }
  }
  const diagnostics = [];
  for (const key of keys) {
    const values = samples.map(sample => sample[key]);
    const span = Math.max(...values) - Math.min(...values);
    if (span < EPSILON) continue;
    let maxStep = 0, maxAcceleration = 0;
    for (let t = 1; t < values.length; t += 1) {
      const step = (values[t] - values[t - 1]) / span;
      maxStep = Math.max(maxStep, Math.abs(step));
      if (t > 1) {
        const previousStep = (values[t - 1] - values[t - 2]) / span;
        maxAcceleration = Math.max(maxAcceleration, Math.abs(step - previousStep));
      }
    }
    // Normalize by each channel's full travel, so scene units, radians, pixels,
    // and opacity receive the same guard. A 1 ms step may traverse at most 1.2%
    // of its range; the velocity may change by at most 0.05% of range per ms.
    // This admits a smooth ~200 ms accent but catches visibility cuts, camera
    // jumps, and piecewise-linear velocity kinks. It is not a quality score.
    assert.ok(maxStep <= .012,
      `${key} has a motion discontinuity (${(maxStep * 100).toFixed(4)}% of travel in 1 ms).`);
    assert.ok(maxAcceleration <= .0005,
      `${key} has a velocity discontinuity (${(maxAcceleration * 100).toFixed(4)}% of travel per ms²).`);
    for (const boundary of studio.STUDIO_MOTION_BOUNDARIES ?? []) {
      const delta = .01;
      const a = numericState(studio.studioMotion(boundary - delta))[key];
      const b = numericState(studio.studioMotion(boundary))[key];
      const c = numericState(studio.studioMotion(boundary + delta))[key];
      const leftVelocity = (b - a) / delta / span;
      const rightVelocity = (c - b) / delta / span;
      assert.ok(Math.abs(rightVelocity - leftVelocity) <= 1e-5,
        `${key} changes velocity abruptly at the ${boundary} ms motion boundary.`);
    }
    diagnostics.push({channel: key, maxStep, maxAcceleration});
  }
  return diagnostics;
}

function checkEasing() {
  assert.equal(typeof studio.ease, 'function', 'The studio must expose its easing curve.');
  close(studio.ease(-1), 0, 'Easing clamps before the beginning');
  close(studio.ease(0), 0, 'Easing begins at zero');
  close(studio.ease(1), 1, 'Easing ends at one');
  close(studio.ease(2), 1, 'Easing clamps after the end');
  const delta = 1e-4;
  for (const endpoint of [0, 1]) {
    const a = studio.ease(endpoint - delta), b = studio.ease(endpoint), c = studio.ease(endpoint + delta);
    close((c - a) / (2 * delta), 0, `Easing has zero velocity at ${endpoint}`, 1e-5);
    close((c - 2 * b + a) / delta ** 2, 0, `Easing has zero acceleration at ${endpoint}`, .002);
  }
}

function visibleMotion(t) {
  const state = structuredClone(studio.studioMotion(t));
  // An invisible mesh can be repositioned off camera without affecting a hold.
  // Its opacity remains in the state so the first visible movement is checked.
  for (const name of ['housing', 'logo']) {
    if (state[name].opacity <= EPSILON) state[name] = {opacity: 0};
  }
  return numericState(state);
}

function checkPreview() {
  assert.equal(typeof studio.studioPreviewTimeline, 'function', 'A separate preview timeline is required.');
  const fps = 24, step = 1000 / fps, preview = studio.studioPreviewTimeline(fps);
  assert.ok(preview.length > 0 && preview.length <= 300, 'The README preview must stay within 300 frames.');
  let elapsed = 0;
  for (const [index, entry] of preview.entries()) {
    close(entry.t, elapsed, `Preview frame ${index} is contiguous`);
    close(entry.t / step, Math.round(entry.t / step), `Preview frame ${index} is on its final output grid`);
    assert.ok(Number.isFinite(entry.durationMs) && entry.durationMs >= step - EPSILON,
      `Preview frame ${index} has a non-positive or sub-frame delay.`);
    if (entry.durationMs > step + EPSILON) {
      const held = visibleMotion(entry.t);
      // Every omitted 24 fps sample must retain the same visible scene pose.
      // Transcript/scroll changes are covered separately by the renderer tests.
      for (let t = entry.t + step; t < entry.t + entry.durationMs - EPSILON; t += step) {
        const sample = visibleMotion(t);
        assert.deepEqual(Object.keys(sample), Object.keys(held), `Preview holds through a visibility change at ${t} ms.`);
        for (const key of Object.keys(held)) close(sample[key], held[key], `Preview holds through ${key} movement at ${t} ms`);
      }
    }
    elapsed += entry.durationMs;
  }
  close(elapsed, EXPECTED_DURATION, 'Preview total duration');
  return preview.length;
}

async function checkInspections(path) {
  const entries = JSON.parse(await readFile(path, 'utf8'));
  assert.ok(Array.isArray(entries) && entries.length >= 2, 'Motion inspections need at least two samples.');
  const frames = entries.map(entry => ({...entry, ...(entry.scene ?? {})}));
  let previous;
  for (const [index, frame] of frames.entries()) {
    const t = entries[index].t;
    assert.ok(Number.isFinite(t), `Inspection ${index} needs a presentation timestamp.`);
    assert.ok(Array.isArray(frame.screenCorners) && frame.screenCorners.length === 4,
      `Inspection ${index} needs four projected screen corners.`);
    for (const corner of frame.screenCorners) {
      assert.ok(Number.isFinite(corner.x) && Number.isFinite(corner.y), `Non-finite screen corner at ${t}.`);
    }
    for (const key of ['housingOpacity', 'logoOpacity']) {
      const value = frame[key] ?? frame.motion?.[key];
      assert.ok(Number.isFinite(value) && value >= 0 && value <= 1, `Inspection ${index} needs valid ${key}.`);
      const expected = studio.studioMotion(t)[key === 'housingOpacity' ? 'housing' : 'logo'].opacity;
      close(value, expected, `Inspection ${index} ${key}`, 1e-5);
    }
    if (previous) {
      const dt = t - previous.t;
      assert.ok(dt > 0, 'Motion inspections must be strictly ordered.');
      assert.ok(dt <= FRAME_MS + EPSILON, 'Motion inspection gaps may not exceed one output frame.');
      // At the 1280 × 720 authored stage, a corner may move at most 2 px/ms
      // (~67 px/frame at 30 fps). This catches teleports while permitting the
      // fast, eased terminal reframe. Check geometry even during opacity fades.
      for (let corner = 0; corner < 4; corner += 1) {
        const a = previous.frame.screenCorners[corner], b = frame.screenCorners[corner];
        const speed = Math.hypot(b.x - a.x, b.y - a.y) / dt;
        assert.ok(speed <= 2, `Projected corner ${corner} jumps at ${t} ms (${speed.toFixed(3)} px/ms).`);
      }
    }
    previous = {t, frame};
  }
  return entries.length;
}

close(studio.STUDIO_DURATION, EXPECTED_DURATION, 'Studio duration');
close(studio.STUDIO_FPS, EXPECTED_FPS, 'Studio output rate');
checkUniformFrames(studio.studioTimeline(), 'Studio timeline');
checkEasing();
const motion = checkMotion();
const previewFrames = checkPreview();
if (options.has('--manifest')) {
  checkUniformFrames(JSON.parse(await readFile(options.get('--manifest'), 'utf8')), 'Rendered manifest');
}
const inspections = options.has('--inspections') ? await checkInspections(options.get('--inspections')) : 0;
console.log(`Studio cadence passed: ${EXPECTED_FRAMES} exact ${EXPECTED_FPS} fps frames, ${EXPECTED_DURATION / 1000} s, ${motion.length} continuous motion channels, ${previewFrames} preview frames${inspections ? `, ${inspections} projected-frame inspections` : ''}.`);
