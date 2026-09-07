// Resolve npm's JavaScript entrypoint instead of launching npm.cmd through a
// shell. Candidate construction is platform-explicit so Windows is testable on
// every runner; the selected file must belong to an npm package installation.
import { readFile, realpath, stat } from "node:fs/promises";
import { posix, win32 } from "node:path";

export function npmCandidates({ execPath, npmExecPath, searchPath = "", platform = process.platform }) {
  const path = platform === "win32" ? win32 : posix;
  const candidates = [];
  const add = (value) => { if (value && path.isAbsolute(value)) candidates.push(path.normalize(value)); };
  add(npmExecPath);
  const nodeDirectory = path.dirname(execPath);
  for (const directory of [nodeDirectory, ...searchPath.split(path.delimiter).map((value) => value.replace(/^"(.*)"$/, "$1"))]) {
    if (!path.isAbsolute(directory)) continue;
    add(path.join(directory, "node_modules", "npm", "bin", "npm-cli.js"));
    add(path.join(directory, "..", "lib", "node_modules", "npm", "bin", "npm-cli.js"));
    // A POSIX npm launcher is normally a symlink to the entrypoint. On Windows
    // npm.cmd itself fails validation, while the sibling package above works.
    add(path.join(directory, "npm"));
  }
  return [...new Set(candidates)];
}

export async function resolveNpmCommand({
  execPath = process.execPath, npmExecPath = process.env.npm_execpath,
  searchPath = process.env.PATH ?? process.env.Path ?? "", platform = process.platform,
} = {}) {
  const path = platform === "win32" ? win32 : posix;
  for (const candidate of npmCandidates({ execPath, npmExecPath, searchPath, platform })) {
    try {
      const entry = await realpath(candidate);
      if (path.basename(entry) !== "npm-cli.js" || !(await stat(entry)).isFile()) continue;
      const packageRoot = path.dirname(path.dirname(entry));
      const pkg = JSON.parse(await readFile(path.join(packageRoot, "package.json"), "utf8"));
      if (pkg.name !== "npm" || pkg.bin?.npm !== "bin/npm-cli.js") continue;
      return { executable: execPath, prefixArgs: [entry], shell: false };
    } catch { /* A missing or unrelated candidate is not an npm installation. */ }
  }
  throw new Error("Could not resolve npm-cli.js from the Node installation or PATH. Install npm alongside Node.");
}

export function withPath(environment, value) {
  // Windows environment names are case-insensitive. Do not let an inherited
  // `Path` silently defeat the no-Python checks when assigning `PATH`.
  return { ...Object.fromEntries(Object.entries(environment).filter(([key]) => key.toLowerCase() !== "path")), PATH: value };
}
