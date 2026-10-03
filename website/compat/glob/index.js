import { globSync as tinyGlobSync } from "tinyglobby";
import path from "node:path";

// This is an implementation replacement, not a copy/fork of fast-glob or
// braces. Only the synchronous APIs used by the two pinned consumers exist.
const allowedOptions = new Set(["cwd", "onlyDirectories"]);
const maxLength = 10000;
const maxDepth = 100;

function validatePattern(pattern) {
  if (typeof pattern !== "string" || pattern.length === 0) {
    throw new TypeError("A glob pattern must be a nonempty string");
  }
  if (pattern.length > maxLength) {
    throw new RangeError("Glob pattern exceeds the 10000-character limit");
  }
  let depth = 0;
  let inClass = false;
  for (let index = 0; index < pattern.length; index++) {
    const character = pattern[index];
    if (character === "\\") {
      index++;
      continue;
    }
    if (character === "[") inClass = true;
    if (character === "]") inClass = false;
    if (inClass) continue;
    if (character === "{" || character === "(") {
      if (++depth > maxDepth) {
        throw new RangeError("Glob pattern exceeds the 100-level nesting limit");
      }
    } else if (character === "}" || character === ")") {
      depth = Math.max(0, depth - 1);
    }
  }
}

function globSync(patterns, options = {}) {
  const list = Array.isArray(patterns) ? patterns : [patterns];
  for (const pattern of list) validatePattern(pattern);
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new TypeError("Glob options must be an object");
  }
  for (const key of Reflect.ownKeys(options)) {
    if (!allowedOptions.has(key)) {
      throw new TypeError(`Unsupported website glob option: ${String(key)}`);
    }
  }
  if (options.cwd !== undefined && typeof options.cwd !== "string") {
    throw new TypeError("Glob cwd must be a string");
  }
  if (options.onlyDirectories !== undefined && typeof options.onlyDirectories !== "boolean") {
    throw new TypeError("Glob onlyDirectories must be a boolean");
  }
  const positivePatterns = list.filter((pattern) => !pattern.startsWith("!"));
  const absolutePatterns = positivePatterns.filter((pattern) => path.isAbsolute(pattern));
  if (absolutePatterns.length !== 0 && absolutePatterns.length !== positivePatterns.length) {
    throw new TypeError("Mixed absolute and relative website glob patterns are unsupported");
  }
  return tinyGlobSync(list, {
    ...options,
    expandDirectories: false,
    absolute: absolutePatterns.length > 0,
  }).map((entry) => entry.length > 1 ? entry.replace(/\/$/, "") : entry);
}

export { globSync as sync, globSync };
export default { sync: globSync, globSync };
