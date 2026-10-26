/** Conservative copy-artifact cleanup. This never detects a provider watermark. */
export function createTextHygiene() {
  const policyVersion = '2026-10-26.1';
  const removable = /[\u200B\u2060\uFEFF]/g;
  const words = new Set('a an and are clear draft hello in is of text the this to world writing'.split(' '));
  const statisticalWatermark = { status: 'not_verified', reason: 'matching_detector_unavailable' };
  function validate(text) {
    if (typeof text !== 'string') throw new TypeError('Text must be a string.');
    if (text.length > 200000) throw new RangeError('Text hygiene input exceeds 200000 UTF-16 units.');
  }
  // A change-detection fingerprint, not authentication or provenance evidence.
  function binding(text) {
    let first = 2166136261; let second = 2246822519;
    for (let i = 0; i < text.length; i += 1) {
      first = Math.imul(first ^ text.charCodeAt(i), 16777619) >>> 0;
      second = Math.imul(second ^ text.charCodeAt(i), 3266489917) >>> 0;
    }
    return `${text.length}:${first}:${second}`;
  }
  function plannedEdits(text) {
    if (/[<>]/.test(text)) return []; // Preserve unknown markup and multiline HTML as a whole.
    const edits = []; let offset = 0; let fence = null; let frontmatter = false;
    for (const line of text.split(/(?<=\n)/)) {
      if (offset === 0 && /^\uFEFF?---\s*$/.test(line)) { frontmatter = true; offset += line.length; continue; }
      if (frontmatter) { if (/^(?:---|\.\.\.)\s*$/.test(line)) frontmatter = false; offset += line.length; continue; }
      const marker = line.match(/^\s*(`{3,}|~{3,})/);
      if (marker) {
        if (!fence) fence = { char: marker[1][0], length: marker[1].length };
        else if (fence.char === marker[1][0] && marker[1].length >= fence.length && /^\s*(?:`+|~+)\s*$/.test(line)) fence = null;
        offset += line.length; continue;
      }
      const plain = line.replace(removable, '');
      // Sentence shape and a small set of prose openers keep unfenced commands
      // and unknown fragments out of this deliberately conservative cleanup.
      const protectedLine = fence || !/^\s*(?:the|this|hello|an?)\b/i.test(plain) || !/[.!?]\s*$/.test(plain)
        || /[()[\]{};&]|(?:^|\s)--?[A-Za-z]/.test(plain)
        || [...plain].some(char => (char.charCodeAt(0) < 32 && !'\t\n\r'.includes(char)) || char.charCodeAt(0) > 126)
        || /^ {4}|^\t|[`"'<>$=\\:|]|https?:|www\.|@|\]\(|\b(?:identifier|variable|function|path|command|token|password|code|regex|formula|equation)\b/i.test(plain)
        || /\b\w+[./_]\w+\b/.test(plain);
      const ordinaryWords = plain.match(/[A-Za-z]+/g) || [];
      if (!protectedLine && ordinaryWords.length >= 2) {
        for (const word of line.matchAll(/[A-Za-z\u200B\u2060\uFEFF]+/g)) {
          const cleaned = word[0].replace(removable, '');
          if (!words.has(cleaned.toLowerCase())) continue;
          for (let i = 1; i < word[0].length - 1; i += 1) {
            const char = word[0][i];
            if ('\u200B\u2060\uFEFF'.includes(char) && /[A-Za-z]/.test(word[0][i - 1]) && /[A-Za-z]/.test(word[0][i + 1])) {
              const start = offset + word.index + i;
              edits.push({ start, end: start + 1, original: char, replacement: '', reason: 'embedded_ascii_copy_artifact' });
            }
          }
        }
      }
      offset += line.length;
    }
    return edits;
  }
  function cleanTextHygiene(text) {
    validate(text);
    const edits = plannedEdits(text);
    const chunks = []; let cursor = 0;
    for (const edit of edits) { chunks.push(text.slice(cursor, edit.start)); cursor = edit.end; }
    chunks.push(text.slice(cursor));
    const cleaned = chunks.join(''); const outputBinding = binding(cleaned);
    for (let i = 0; i < edits.length; i += 1) {
      edits[i].outputStart = edits[i].start - i;
      edits[i].outputBinding = outputBinding;
    }
    return { text: cleaned, edits, status: edits.length ? 'cleaned' : 'unchanged', policyVersion,
      offsetUnit: 'utf16', statisticalWatermark: { ...statisticalWatermark } };
  }
  function inspectTextHygiene(text) {
    const result = cleanTextHygiene(text); const findings = [];
    const actionable = new Set(result.edits.map(edit => edit.start));
    for (let i = 0; i < text.length;) {
      const cp = text.codePointAt(i);
      if (cp === 0xAD || cp === 0xFEFF || (cp >= 0x200B && cp <= 0x200F)
        || (cp >= 0x202A && cp <= 0x202E) || (cp >= 0x2060 && cp <= 0x2069)
        || (cp >= 0xFE00 && cp <= 0xFE0F) || (cp >= 0xE0000 && cp <= 0xE01EF)) {
        findings.push({ start: i, codePoint: `U+${cp.toString(16).toUpperCase().padStart(4, '0')}`,
          disposition: actionable.has(i) ? 'removable' : 'preserved' });
      }
      i += cp > 0xFFFF ? 2 : 1;
    }
    return { ...result, text, findings, status: 'inspected' };
  }
  function reverseTextHygiene(text, edits) {
    validate(text);
    if (!Array.isArray(edits) || edits.length > 200000) throw new TypeError('Edits must be a bounded array.');
    const chunks = []; let cursor = 0; let previous = -1; const outputBinding = binding(text);
    for (let i = 0; i < edits.length; i += 1) {
      const edit = edits[i];
      if (!edit || typeof edit !== 'object' || !Number.isInteger(edit.start) || edit.start < 1 || edit.start > text.length + edits.length
        || !Number.isInteger(edit.outputStart) || edit.outputStart < 0 || edit.outputStart > text.length
        || edit.start <= previous || edit.end !== edit.start + 1
        || !'\u200B\u2060\uFEFF'.includes(edit.original) || edit.original.length !== 1
        || edit.replacement !== '' || edit.outputBinding !== outputBinding
        || edit.outputStart !== edit.start - i) throw new Error('Cleanup plan does not match this text.');
      previous = edit.start;
      chunks.push(text.slice(cursor, edit.outputStart), edit.original); cursor = edit.outputStart;
    }
    chunks.push(text.slice(cursor));
    return chunks.join('');
  }
  return Object.freeze({ cleanTextHygiene, inspectTextHygiene, reverseTextHygiene });
}

const helpers = createTextHygiene();
export const cleanTextHygiene = helpers.cleanTextHygiene;
export const inspectTextHygiene = helpers.inspectTextHygiene;
export const reverseTextHygiene = helpers.reverseTextHygiene;
