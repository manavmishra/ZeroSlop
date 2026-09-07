# Zero Slop REST API

`POST https://mcp.zero-slop.ai/v1/deslop` edits one draft through the same pipeline
as the hosted MCP `deslop` tool. It returns the same 14 fields, including the edit,
writing scores, source-check result, and review status.

The [OpenAPI 3.1.2 contract](https://mcp.zero-slop.ai/openapi.json) is generated
from the schemas used to validate MCP and REST requests and results. Import it
into an OpenAPI-compatible client or documentation tool.

Use the [API sandbox](https://zero-slop.ai/sandbox/) to inspect a simulated result
before sending a draft. Its live mode requires an explicit request and uses this
same endpoint.

## Send a draft

```sh
curl --fail-with-body --max-time 75 --include https://mcp.zero-slop.ai/v1/deslop \
  -H 'Content-Type: application/json' \
  --data '{"text":"It is important to note that Maya owns the pricing review. The team will decide on Friday.","genre":"professional","audience":"The product team"}'
```

| Field | Accepted value |
|---|---|
| `text` | Required, nonempty string; up to 20,000 Unicode code points after trimming |
| `genre` | `general` (default), `social`, `email`, `research`, or `professional` |
| `audience` | Optional string, up to 200 Unicode code points after trimming |

Lengths count Unicode code points; a combined emoji or accented character can contain more than one.
Send UTF-8 JSON in the body, never a URL query. The body limit is 128 KiB, including
JSON escaping. Compressed bodies are not accepted. Unknown properties are ignored.

Call from your application server. Browser access is enabled only for the Zero Slop
site at `https://zero-slop.ai` and `https://www.zero-slop.ai`; other sites should
call from their servers. CORS is a browser policy, not authentication.

Access is free, without an API key. REST and MCP share capacity and usage limits,
including a daily hosted allowance and a short client cooldown. The allowance can
run out; it does not reserve capacity for an application. Availability is best
effort, with no uptime SLA. Offline skill checks and CLI scoring stay free and do
not consume this hosted allowance.

Current safety limits allow at most five model calls per client network per UTC
day and two per minute, shared across REST, MCP, CLI editing, and `/try/`.
Shared networks can reach those limits together. A separate global limit reserves
up to 8,000 estimated Workers AI neurons per UTC day before inference; it can
stop calls before the client limit is reached. Reservations are conservative and
are not refunded after timeouts. New model calls pause during the last minute
before the UTC reset. These are capacity ceilings, not a guaranteed allocation.

The service records aggregate REST call counts, result categories, model attempts,
quota rejections, and latency. Drafts, rewrites, IP addresses, email addresses and
stable user identifiers are excluded from this telemetry. Calls are not unique
users, and model attempts are not billable token counts. See the
[security policy](../SECURITY.md) for the field list and retention.

## Working language examples

The [example directory](../integrations/api-examples/README.md) contains runnable
clients with 75-second timeouts, structured error handling, and an explicit check
before the returned text can pass to an automated step.

| Language | Source | HTTP client |
|---|---|---|
| curl | [Shell example](../integrations/api-examples/curl/deslop.sh) | curl; jq reads the result |
| JavaScript | [Node.js example](../integrations/api-examples/javascript/deslop.mjs) | Built-in `fetch` |
| TypeScript | [Typed Node.js example](../integrations/api-examples/typescript/deslop.ts) | Built-in `fetch` |
| Python | [Python example](../integrations/api-examples/python/deslop.py) | Standard-library `urllib.request` |
| Java | [Java example](../integrations/api-examples/java/src/main/java/Deslop.java) | JDK `HttpClient`; Jackson for JSON |
| C# | [.NET example](../integrations/api-examples/csharp/Program.cs) | `HttpClient` and `System.Text.Json` |
| Go | [Go example](../integrations/api-examples/go/main.go) | Standard-library `net/http` |
| Rust | [Rust example](../integrations/api-examples/rust/src/main.rs) | reqwest and serde_json |

Each example reads one request object from stdin, sends one POST, and preserves
the complete JSON response. Exit `0` means the approval condition below passed;
exit `3` means review is required. HTTP and transport failures exit `1`. Check
the exit code before extracting `text`; an HTTP `200` alone is insufficient.
These are examples to adapt within an application, not separate SDKs.

## Read the result

HTTP `200` means the pipeline returned a result. It does not mean the edit passed
every check.

| `status` | What to do |
|---|---|
| `rewritten` | Review the edit; the model edit passed the local writing and source checks |
| `already_clear` | Keep the original; no editing-model call was needed |
| `rewritten_with_warnings` | Read `note` and review the result before using it |
| `unchanged_no_better_version` | Keep the original; no better version was selected |
| `unchanged_verification_failed` | Keep the original; proposed edits failed source checks |
| `unchanged_service_unavailable` | Keep the original; the model did not yield a usable edit |

The successful response contains these 14 fields:

| Field | Meaning |
|---|---|
| `text` | Returned draft, which may be unchanged |
| `status` | One of the six outcomes above |
| `before`, `after` | Writing reports: score, flagged phrases, readability, rhythm, punctuation, layout, and register checks |
| `scoreChange` | After score minus before score |
| `factsPreserved` | Whether tracked source details survived the checks |
| `passedFinalChecks` | Whether the rewritten text passed the final checks |
| `independentModelChecks` | Count of independent model checks; currently zero |
| `modelRequests` | Editing-model requests made, zero or one |
| `rolesCompleted` | Completed pipeline responsibilities |
| `finishingRounds` | Additional local finishing rounds |
| `scorerVersion` | Deployed Zero Slop release |
| `durationMs` | Server processing time in milliseconds |
| `note` | Review guidance, including any limitations |

`scoreChange` is after minus before, so a negative value means the measured score fell.
The writing score is not a probability that AI wrote the draft.

For an automation that must stop on a warning, use this condition:

```js
const approved = result.factsPreserved === true && (
  (result.status === "already_clear" && result.modelRequests === 0 &&
   result.scoreChange === 0 && result.before.score === result.after.score) ||
  (result.status === "rewritten" && result.passedFinalChecks === true)
);
```

`already_clear` has `passedFinalChecks: false` because editing-model checks were not
needed. Do not reject it solely on that boolean. Source checks protect tracked
details; they cannot certify factual truth or every change in meaning. Human review
remains necessary before publication.

## Errors and retries

Errors use `application/problem+json` with `type`, `title`, `status`, `detail`,
`code`, and `requestId`. Their details do not echo drafts, model responses, or secrets.

| HTTP status | Meaning |
|---|---|
| `400` | Invalid JSON, UTF-8, declared length, or input fields |
| `403` | `forbidden_origin` or `forbidden_preflight`; use an allowed first-party browser request or call from your server |
| `405` | Wrong method; use `POST` |
| `408` | The request body did not arrive within 10 seconds |
| `413` | The JSON body exceeds 128 KiB |
| `415` | Unsupported media type or compression |
| `429` | `capacity_limit` or `usage_limit`; respect `Retry-After` |
| `503` | `budget_unavailable` if the usage gate could not complete, or `service_unavailable` if no safely scored result was available |

For example, a usage-limit response has this shape; values here are illustrative:

```json
{
  "type": "about:blank",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "The free hosted allowance is currently exhausted. Try again after the indicated delay.",
  "code": "usage_limit",
  "requestId": "11111111-1111-4111-8111-111111111111"
}
```

The `Retry-After` response header gives the minimum delay in seconds. Read it
from the header rather than parsing `detail`. Keep the problem code and request
ID for troubleshooting without logging the draft or result.

Allow 75 seconds on the client. The service makes at most one editing-model request;
scoring and source checks add their own bounded work. A client timeout or cancellation
does not guarantee upstream work stopped. Do not retry automatically after an uncertain
outcome. If a user chooses to retry a `429`, wait at least the `Retry-After` delay.

The API does not store drafts or results for idempotency. Repeated POSTs are separate
calls, may repeat work, and are not guaranteed to return identical text.

## Privacy and versioning

The draft is sent to Zero Slop's hosted service and processed in memory. The upstream
editing service must confirm `stored: false`; drafts and rewrites are not cached or logged by this
service. Aggregate operational counts and short-lived daily hashed client counters
support usage limits and abuse controls. See [SECURITY.md](../SECURITY.md) and
the [hosted-service terms](https://zero-slop.ai/terms/).

`/v1` identifies the HTTP contract. `scorerVersion` identifies the deployed Zero Slop
release. Clients should accept new optional response fields and treat any unrecognized
result status as requiring review. The OpenAPI document is served by the same Worker
as the API, so its version follows the deployment.
