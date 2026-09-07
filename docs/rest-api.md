# Zero Slop REST API

`POST https://mcp.zero-slop.ai/v1/deslop` edits one draft through the same pipeline
as the hosted MCP `deslop` tool. It returns the same 14 fields, including the edit,
writing scores, source-check result, and review status.

The [OpenAPI 3.1.2 contract](https://mcp.zero-slop.ai/openapi.json) is generated
from the schemas used to validate MCP and REST requests and results. Import it
into an OpenAPI-compatible client or documentation tool.

## Send a draft

```sh
curl --fail-with-body --max-time 75 https://mcp.zero-slop.ai/v1/deslop \
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

Call from your application server. The service does not enable cross-origin browser
requests. Access is free, without an API key, and shares MCP's capacity limiter.
Capacity is best effort; there is no reserved quota or uptime SLA.

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

The response also contains `before` and `after` writing reports, `scoreChange`,
`factsPreserved`, `passedFinalChecks`, `independentModelChecks`, `modelRequests`,
`rolesCompleted`, `finishingRounds`, `scorerVersion`, `durationMs`, `text`, and `note`.
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
| `405` | Wrong method; use `POST` |
| `408` | The request body did not arrive within 10 seconds |
| `413` | The JSON body exceeds 128 KiB |
| `415` | Unsupported media type or compression |
| `429` | Shared capacity reached; respect `Retry-After` |
| `503` | No safely scored result was available |

Allow 75 seconds on the client. The service makes at most one editing-model request;
scoring and source checks add their own bounded work. A client timeout or cancellation
does not guarantee upstream work stopped. Do not retry automatically after an uncertain
outcome. If a user chooses to retry a `429`, wait at least the `Retry-After` delay.

The API does not store drafts or results for idempotency. Repeated POSTs are separate
calls, may repeat work, and are not guaranteed to return identical text.

## Privacy and versioning

The draft is sent to Zero Slop's hosted service and processed in memory. The upstream
editing service must confirm `stored: false`; drafts and rewrites are not cached or logged by this
service. Aggregate operational counts remain. See [SECURITY.md](../SECURITY.md) and
the [hosted-service terms](https://zero-slop.ai/terms/).

`/v1` identifies the HTTP contract. `scorerVersion` identifies the deployed Zero Slop
release. Clients should accept new optional response fields and treat any unrecognized
result status as requiring review. The OpenAPI document is served by the same Worker
as the API, so its version follows the deployment.
