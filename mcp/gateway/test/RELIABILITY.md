# Local hosted reliability verification

Run from `mcp/gateway` after `npm ci`, using the Node version required by this
package. The live website source must also be checked out locally; the harness
imports its actual editor and budget helper instead of maintaining a copy.

```sh
ZERO_SLOP_TEST_PAGES_ROOT=/absolute/path/to/ZSWebpage node test/reliability.mjs
```

The default website location is `../../../ZSWebpage` relative to this directory.
`--disconnect-only` runs only the socket-cancellation checks. Only the default
full run covers the soak, concurrency, fault and deadline checks. JSON evidence
is written to stdout; phase progress goes to stderr. The full run takes about
three minutes on a development machine. It is a maintainer check, not a runtime
skill or an end-user benchmark.

## What it exercises

- Real HTTP/TCP requests to the direct local **workerd** socket, not just calls
  to an imported `fetch` function.
- The canonical gateway and live-site editor code. Only the scorer, model,
  coarse rate limiter and analytics delivery are synthetic. No AI binding or
  remote production binding is loaded. Outbound fetches are intercepted by a
  local editor entrypoint; every other destination is rejected. Miniflare
  telemetry is disabled. The signing key is random, local and never reported.
- A 60-second paced soak: 600 clean REST requests at 10 requests/second, with
  measured p50/p95/p99/max latency and no model calls.
- A 48-request concurrent dirty-draft burst against the actual SQLite budget
  implementation; the 8,000-neuron hard cap, stored reservation total and
  post-eviction rejection are checked. A 16-request same-client burst checks
  the two-per-minute allowance. Every phase uses a fresh local budget object;
  the production limits are not raised.
- Missing, throwing, malformed and late quota gates; failed, malformed and
  stalled scorers; failed or abort-ignoring models. Quota errors must be 429
  with retry guidance or fail-closed 503. Model failures must not retry or
  report an approved rewrite. Late reservations remain consumed.
- The actual 36-second shared pipeline deadline, the scorer's eight-second
  deadline, the editor's 24-second deadline and the MCP body's ten-second
  deadline. A stalled MCP upload returns a sanitized 408 before scoring.
- Real TCP resets before the gate, during reservation and during an
  abort-ignoring model for REST/MCP and the common web editor. Tests require
  incoming abort observation, prompt handler/result settlement, no model
  starts after known cancellation, no retries and no refunds. Before outbound
  editor dispatch, cancelled gateway telemetry reports zero model requests;
  after dispatch it remains unknown, not a fabricated zero.

## Limits of this evidence

A complete HTTP/1 upload followed by a graceful TCP FIN is not necessarily
classified as cancellation by local workerd. The harness records this separately;
one budgeted request may finish. A TCP reset does trigger the tested abort path.
HTTP/2, browser, CDN and proxy disconnect behavior are not certified here.

Cancellation bounds how long this service waits. It cannot guarantee that a
provider which ignores its signal stops computing. An uncertain reservation is
never refunded. The fixture retains fake work with `waitUntil` only so late
outcomes can be inspected; production does not deliberately keep inference alive
this way. Test-only state, control routes and the RPC storage-inspection adapter
must never be deployed.

This is bounded regression evidence, **not an enterprise SLA**, long-duration
load certification, model quality/latency benchmark, account-wide billing cap,
or proof of production regional capacity. Local workerd does not emulate all
edge CPU/subrequest limits, network hops or distributed storage failures. Existing
Durable Object runtime tests separately cover expiry, UTC rollover, malformed
reservations and storage-alarm failures.

The incoming signal flag follows [Cloudflare's compatibility documentation](https://developers.cloudflare.com/workers/configuration/compatibility-flags/#enable-requestsignal-for-incoming-requests).
The local runner uses the installed Miniflare API/types, including its documented
v4-options converter and direct-socket/storage-inspection interfaces. The pinned
lockfile determines the runtime used; no dependency is downloaded by the harness.
