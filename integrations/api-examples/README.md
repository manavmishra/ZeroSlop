# REST examples

These examples call `POST https://mcp.zero-slop.ai/v1/deslop` directly. They use
ordinary HTTP clients, so applications do not need a Zero Slop SDK or API key.
Each program reads one JSON request from stdin and sends it once.

Run the commands below from this directory. The included `request.json` contains
a synthetic draft. Running an example sends that draft to the hosted service;
the tests use a local fixture server and make no model calls.

| Language | Requirement | Run |
|---|---|---|
| [curl](curl/deslop.sh) | curl and jq | `sh curl/deslop.sh < request.json` |
| [JavaScript](javascript/deslop.mjs) | Node.js 22+ | `node javascript/deslop.mjs < request.json` |
| [TypeScript](typescript/deslop.ts) | Node.js 22.18+ | `node typescript/deslop.ts < request.json` |
| [Python](python/deslop.py) | Python 3.9+; standard library | `python3 python/deslop.py < request.json` |
| [Go](go/main.go) | Go 1.22+; standard library | Compile below, then run `go/bin/deslop` |
| [Java](java/src/main/java/Deslop.java) | Java 17+, Maven, Jackson for JSON | Compile below, then run `Deslop` |
| [C#](csharp/Program.cs) | .NET 8+; standard library | Compile below, then run `Deslop.dll` |
| [Rust](rust/src/main.rs) | Rust and Cargo; reqwest and serde_json | Compile below, then run the binary |

Java uses the JDK HTTP client and Jackson to read JSON. On macOS and Linux:

```sh
mvn -q -f java/pom.xml compile dependency:copy-dependencies
java -cp 'java/target/classes:java/target/dependency/*' Deslop < request.json
```

On Windows, separate Java classpath entries with `;` instead of `:`. The shell
commands here use POSIX input redirection; adapt that redirection to your shell.

Compile Go, C#, and Rust once before making requests. Run the Go binary directly
to preserve its exit code; `go run` reports a failing program as exit `1`.

```sh
mkdir -p go/bin
go build -o go/bin/deslop go/main.go
go/bin/deslop < request.json

dotnet build csharp/Deslop.csproj --output csharp/bin/example
dotnet csharp/bin/example/Deslop.dll < request.json

cargo build --manifest-path rust/Cargo.toml
rust/target/debug/zero-slop-rest-example < request.json
```

## Results and failures

Every HTTP `200` result is printed as complete JSON on stdout, preserving all
14 fields and any future additions. Check the process exit code before using
`text` in another step:

| Exit code | Meaning |
|---|---|
| `0` | `rewritten` passed the source and final-check flags, or `already_clear` returned matching scores without a model request |
| `3` | Review required; stdout still contains the result and its `note` |
| `1` | HTTP, transport, or JSON error; keep the original |

The examples require all 14 fields and check the types and values used by the
approval decision. They do not implement the full nested OpenAPI schema. Use the
[published contract](https://mcp.zero-slop.ai/openapi.json) if your application
needs full response validation. A type declaration alone does not validate a
response. Unknown result statuses require review.

HTTP failures with a JSON response body print a JSON object to stderr with
`httpStatus`, `retryAfter`, and the complete `problem`, including its `code` and
`requestId`. Transport failures and non-JSON responses print a short diagnostic.
`429` can mean shared capacity is busy or the
free usage allowance has been reached; the problem code distinguishes them.
`503` with `budget_unavailable` means the usage check could not complete safely.

Requests have a 75-second deadline and do not follow redirects or automatically
retry. After a `429`, wait at least the `Retry-After` delay before a deliberate
retry. A timeout can leave the outcome unknown; cancellation does not guarantee
that upstream processing stopped. Preserve the original until the result has
been reviewed. Passing the flags does not establish factual truth or make a
draft ready to publish without human review.

## Test without sending drafts

```sh
node --test samples.test.mjs
```

The runner sends the fixed request to a loopback HTTP server. It exercises all
six result statuses, malformed JSON and approval flags, future fields and statuses,
structured errors, `Retry-After`, and a redirect. Each case must make exactly one
request and preserve the returned JSON.

JavaScript, TypeScript, Python, and curl run when their runtimes are available.
Go compiles into a temporary directory. To include the other compiled examples
after the build commands above, set:

```sh
export ZERO_SLOP_JAVA_CP="$PWD/java/target/classes:$PWD/java/target/dependency/*"
export ZERO_SLOP_CSHARP_DLL="$PWD/csharp/bin/example/Deslop.dll"
export ZERO_SLOP_RUST_EXAMPLE="$PWD/rust/target/debug/zero-slop-rest-example"
ZERO_SLOP_REQUIRE_ALL_EXAMPLES=1 node --test samples.test.mjs
```

Missing runtimes are reported as skips in a normal local run. The repository's
`REST language examples` CI job builds and requires all eight languages.
`ZERO_SLOP_API_URL` selects an endpoint for testing; configure it yourself and
never take its value from a draft. The default is the public HTTPS endpoint.

See the [REST reference](../../docs/rest-api.md) for input limits, privacy, free
shared capacity, and all response fields. Offline skill checks and CLI scoring
remain free and do not consume the hosted allowance.
