# Zero Slop CLI

Use `deslop` for hosted editing with MCP parity. Use `score` for offline checks.

```sh
npm install --global zero-slop@2.11.1
zero-slop deslop draft.md --genre professional
zero-slop deslop - --genre email < draft.txt
zero-slop deslop draft.md --json --require-approved
zero-slop score draft.md -- --json
```

Use Node.js 22 or newer for hosted editing. Offline scoring also requires Python 3.
The npm package includes the skill and its local checks; no separate model ships.

On macOS, [Homebrew](https://github.com/manavmishra/homebrew-zero-slop) installs
the same npm CLI plus Node and Python:

```sh
brew install manavmishra/zero-slop/zero-slop
```

The tap pins a tested npm release; a new npm version may arrive before its
Homebrew update. Linux Homebrew has not been tested.

`deslop` reads exactly one file or standard input, sends the draft to
`https://mcp.zero-slop.ai/mcp`, and writes the returned text to standard output.
It never edits a source file in place. Warnings go to standard error. Capture
standard output only when you intend to save it.

## Options and results

| Option | Purpose |
|---|---|
| `--genre` | `general`, `social`, `email`, `research`, or `professional` |
| `--audience` | Intended reader or destination, up to 200 Unicode code points |
| `--json` | Full MCP result, including all check fields and status |
| `--require-approved` | Exit nonzero if the result needs review |
| `--timeout` | Remote request deadline in seconds: 75 by default, up to 300 |

The draft limit is 20,000 Unicode code points after trimming. Directory uploads,
automatic chunking, and automatic retries are not supported. Only the draft and
supplied genre/audience are transmitted; filenames and private learning profiles
stay local. See the [remote-service privacy boundary](../SECURITY.md#remote-service-boundary).

Inspect the [six result statuses](rest-api.md#read-the-result). In particular,
`rewritten_with_warnings` is an edit to review, not an approved result.
`already_clear` returns the original without an editing-model request.

| Exit code | Meaning |
|---|---|
| `0` | A valid result was returned; inspect its status before using it |
| `1` | Transport or service failure |
| `2` | Invalid input or options |
| `3` | `--require-approved` rejected the result; the result is still printed |
| `124` | Remote request timed out |
| `130` / `143` | Interrupted / terminated |

A timeout or cancellation may not stop hosted processing. The CLI does not replay
the request. Review any returned status or error before choosing to send the draft again.

Hosted editing shares its free allowance with MCP, REST, and `/try/`. A
`usage_limit` error exits `1`; JSON errors include `httpStatus: 429` and, when
provided, `retryAfterSeconds`. Wait at least that long before a manual retry.
`budget_unavailable` (`503`) means capacity could not be checked, so no new model
request was started. Offline scoring does not consume this allowance.

Hosted calls are included in aggregate service metrics: channel, result status,
model attempts, and latency. A fixed CLI-family/major-version header identifies
the entry channel on the requests already being sent; no extra tracking request
is made. It does not identify a person or installation. Offline commands send no
analytics. See the [security policy](../SECURITY.md) for the complete field list.

## Offline scoring

```sh
zero-slop score draft.md -- --json
zero-slop score - -- --json < draft.txt
zero-slop score docs/ -- --batch --json --gate 25
```

The scorer does not transmit drafts. A numerical gate fails when the score exceeds
its threshold; equality passes. Its score measures writing patterns, not authorship
or factual truth. Hosted editorial approval includes additional checks and should
not be inferred from the number alone.

## Install the portable skill

```sh
zero-slop install
```

The installed skill runs inside a compatible AI assistant. Its editing follows that
assistant's privacy settings. Installing the skill does not send your writing to
the hosted service.
