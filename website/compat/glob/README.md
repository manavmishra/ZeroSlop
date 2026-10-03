# Website-only glob implementation replacement

This private, source-controlled package replaces the **implementation** of the
transitive `fast-glob` dependency for the retained website snapshot. It contains
no fast-glob, micromatch or braces source. It uses the already-admitted
`tinyglobby@0.2.17` implementation instead, removing the vulnerable braces chain
without suppressing the unchanged audit gate or downgrading tooling.

It is deliberately not a general fast-glob replacement. It exposes only `sync`
and `globSync`, accepting string/string-array patterns, `cwd` and
`onlyDirectories`. Other options fail explicitly. Patterns are limited to10000
characters and100 nested braces/parentheses before glob parsing. No network,
credential, subprocess or installation hook is added.

Absolute patterns produce absolute results, relative patterns produce relative
results, and directories have no added trailing slash, matching the consumers'
previous behavior. Mixed absolute/relative positive pattern arrays are rejected;
neither pinned consumer needs them. Empty pattern arrays produce no matches.

The pinned consumers are:

- `@next/eslint-plugin-next@16.2.6`: `get-root-dirs` calls `globSync` with
  `onlyDirectories:true`. All existing lint rules remain enabled.
- `vite-plugin-dynamic-import@1.6.0`, reached through
  `vite-plugin-commonjs@0.10.4` and `vinext@1.0.0-beta.8`: `globFiles` calls
  `sync` with the importer's directory as `cwd`. CommonJS conversion and
  dynamic-import discovery remain active.

Primary sources:

- [Next consumer source](https://github.com/vercel/next.js/blob/v16.2.6/packages/eslint-plugin-next/src/utils/get-root-dirs.ts)
- [Dynamic-import consumer source](https://github.com/vite-plugin/vite-plugin-dynamic-import/blob/v1.6.0/src/index.ts)
- [Tinyglobby source](https://github.com/SuperchupuDev/tinyglobby)
- [Official migration guide](https://superchupu.dev/tinyglobby/migration):
  `expandDirectories:false` preserves fast-glob's directory-expansion behavior.
- [Braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm):
  no official patched version was available when this replacement was prepared.

The website's npm override retains upstream import names solely for module
resolution; the installed package identifies itself as this adapter. The
lockfile and tests must show that neither micromatch nor braces is installed.
The root declares `fast-glob` as `file:compat/glob`; npm's `$fast-glob` override
references that same direct dependency specification for both consumers.
Ordinary `npm ci` and `npm ls --all` must resolve both to `website/compat/glob`
and report a valid dependency tree. No consumer-relative override is used.
The adapter uses native synchronous ESM without top-level await. Node22.13.0
or newer, already required by this website, supports loading it from the pinned
CommonJS consumers through `require(esm)` as well as through ESM imports.
Both loading paths are regression-tested; no lint rule is disabled.
The ESM default export is the same two-function object required by the
dynamic-import consumer's default import; named exports support Next's
CommonJS access. Node's CommonJS interop adds an `__esModule` marker.

- [npm override references](https://docs.npmjs.com/cli/v10/configuring-npm/package-json/#overrides)
- [Node synchronous ESM loading](https://nodejs.org/docs/latest-v22.x/api/modules.html#loading-ecmascript-modules-using-require)

Consumer upgrades require rerunning the compatibility fixtures, lint, build,
rendered-page tests, and unchanged dependency audit. This adapter does not
authorize deploying the retained website snapshot; its refusal guard remains.
