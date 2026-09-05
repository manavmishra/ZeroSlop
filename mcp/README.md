# Zero Slop MCP

The Zero Slop MCP exposes one stateless `deslop` tool over Streamable HTTP. It
accepts prose from any MCP client and returns the safest source-preserving edit,
the exact before and after writing reports, fact-preservation status, and final
review metadata.

Canonical production endpoint: `https://mcp.zero-slop.ai/mcp`

## Architecture

```text
MCP client
    |
    | Streamable HTTP, typed input and output
    v
gateway Worker
    |-- per-colocation capacity limit
    |-- 36 second end-to-end budget
    |-- one editor request, then local checks
    |
    | service binding                    | HTTPS, HMAC, no-store
    v                                    v
private scorer Worker              one Workers AI editor
exact Zero Slop 2.8.11              same composite edit as /try/
```

The split is deliberate. The TypeScript gateway owns the public protocol,
input schema, deadlines, release policy, and security headers. A private
Python Worker runs byte-for-byte copies of the shipped scorer modules. The
five AI editorial responsibilities share one composite response, exactly as
they do on `/try/`. The editor calls one binding-native Workers AI model at
temperature zero. It has no provider ladder, model retry, or second finishing
request. The scorer and source checks run before and after that response.

The gateway marks a rewrite fully checked only when all of these are true:

- deterministic reranking finds no dropped or invented facts;
- the final writing score is below 25;
- register and document-shape checks are clean;
- the one editorial response completed the copy-desk, read-aloud, and
  fresh-eyes responsibilities; and
- the final local recheck approves the exact text returned.

Missing an editorial target does not start another model request. The safest
source-preserving edit comes back with a clear review warning. If the one model
request fails or changes protected material, a conservative local editor removes
known stock wording without changing source details. It follows the same fixtures as
the installed `scripts/rescue.py` command and the browser demo. A clean source returns
after scoring and is never sent to the model.

## Connect

Codex:

```sh
codex mcp add zero-slop --url https://mcp.zero-slop.ai/mcp
```

Claude Code:

```sh
claude mcp add --transport http zero-slop --scope user https://mcp.zero-slop.ai/mcp
```

ChatGPT desktop: open **Settings → MCP servers → Add server**, select
Streamable HTTP, and paste the canonical endpoint. Save, restart, and use
`/mcp` to verify it.

Claude and Cowork: open **Customize → Connectors → + → Add custom connector**,
paste the canonical endpoint, then enable Zero Slop from **+ → Connectors** in
the conversation. A Team or Enterprise owner adds it under organization
connector settings.

Any other remote MCP client can add `https://mcp.zero-slop.ai/mcp` as a
Streamable HTTP server with no authentication.

The single tool accepts:

```json
{
  "text": "The complete draft",
  "genre": "general",
  "audience": "Optional intended reader"
}
```

`genre` is one of `general`, `social`, `email`, `research`, or `professional`.
Drafts are capped at 20,000 characters.

## Privacy and security contract

- MCP requests set `noStore: true`. The production editor endpoint skips both
  Cache API reads and writes, and the gateway rejects a response unless it
  explicitly confirms `stored: false`.
- The gateway signs the exact editor request body with HMAC-SHA-256. The editor
  accepts connector mode only with a valid signature less than 60 seconds old;
  the shared secret never reaches an MCP client.
- The editor requests no storage. Connector
  drafts and rewrites are not logged by Zero Slop. Operational logs contain
  only status, sizes, scores, timings, and provider metadata.
- First-party Analytics Engine telemetry records aggregate request, client,
  region, quality, latency, and capacity fields. It does not record drafts,
  rewrites, prompts, detected phrases, IP addresses, raw user agents, cookies,
  email addresses, or stable user or session identifiers. Client
  initializations are connections, not unique-user counts.
- The telemetry dataset is retained for three months. The existing daily Zero
  Slop report receives sampling-aware aggregates for connections, calls,
  result mix, safe-response rate, before and after scores, p50 and p95 latency,
  client and genre mix, geography, and capacity rejects. Collector failures do
  not affect an MCP response or suppress the rest of the report.
- The private scorer has no public route. It is reachable only through the
  Cloudflare service binding and cannot load a maintainer's private learning
  overlay.
- Tool input is treated as untrusted data. Callers cannot select a system
  prompt, provider URL, or model.
- Host and Origin validation, strict schemas, bounded packet sizes, a per-call
  abort, an end-to-end deadline, and a per-colocation capacity ceiling bound
  abuse and cost.
- Errors never include source text, generated text, stack traces, or provider
  credentials.
- Thirty-two SQLite-backed Durable Object shards keep lifetime aggregate counters for MCP
  initializations, tool calls, completed results, delivered rewrites, warnings,
  failures, and capacity rejects. It stores no draft, rewrite, prompt, IP,
  cookie, user ID, or raw user agent. MCP clients do not provide a stable
  installation identifier, so initializations are never presented as unique
  installs. Each increment is atomic and carries a short-lived idempotency key,
  so a transient retry cannot count the same event twice. The report reads every
  shard plus the original `global` object, so deployment of the sharded design
  does not reset or discard earlier totals.
- `GET /internal/counters` exposes those totals only to the daily report. It
  requires a separate `REPORT_SHARED_SECRET`; do not reuse the editor signing
  secret. Store the same random value as a Worker secret and as the
  `MCP_REPORT_TOKEN` GitHub Actions secret in `manavmishra/ZSWebpage`.

The scorer Worker uses Cloudflare's Python Workers runtime, which Cloudflare
currently labels beta. That risk is isolated behind a private service binding;
the gateway health check pins the scorer version, and any scorer failure leaves
the caller's source unchanged. The production scorer can be moved to another
private runtime without changing the public MCP schema.

The public no-auth endpoint intentionally optimizes for a one-command install.
It is still a metered service: keep Cloudflare usage alerts and account-level
spend controls enabled. The application rate limit is a capacity guard, not a
substitute for an account billing limit.

## Source layout

- `gateway/`: standards-based MCP server and release pipeline.
- `scorer/`: private Python scorer Worker.
- `scripts/sync_scorer.py`: copies the six shipped scorer artifacts and writes
  a SHA-256 manifest.
- `scripts/test_scorer.py`: rejects stale copies and exercises score, report,
  rerank, and fidelity behavior.
- The editor endpoint lives in the production website repository at
  `github.com/manavmishra/ZSWebpage`.

## Local verification

Requirements: Node.js 22 or newer, Python 3.13, and `uv`.

```sh
python3 mcp/scripts/sync_scorer.py
python3 mcp/scripts/test_scorer.py

cd mcp/gateway
npm ci
npm run check
npm run dry-run

cd ../scorer
npm ci
uv sync
npm run dry-run
```

`npm run check` includes fast Node tests and a Vitest suite inside the Workers
runtime. The runtime suite exercises concurrent SQLite increments, input
rejection, and persistence across Durable Object eviction.

The vendored scorer is release-pinned. A read-only integrity check is safe at
any time:

```sh
python3 mcp/scripts/sync_scorer.py --check
```

Moving it to a new release is intentionally explicit:

```sh
python3 mcp/scripts/sync_scorer.py --version X.Y.Z
```

That command copies the current scorer sources and records their hashes. Review
the resulting diff, update the gateway's `SCORER_VERSION`, and rerun every gate
before deployment. Merely updating the root package cannot silently relabel the
production MCP scorer.

For both Workers in one local process, first run `uv sync` in `mcp/scorer`,
then from `mcp/` run:

```sh
./gateway/node_modules/.bin/wrangler dev \
  -c gateway/wrangler.jsonc \
  -c scorer/wrangler.jsonc \
  --port 8792
```

`GET http://localhost:8792/health` must report the same version for the gateway
and scorer before protocol tests run.

## Deployment

Deploy in this order:

1. Generate one random secret of at least 32 characters. Store the same value
   as the encrypted Pages secret `MCP_EDITOR_SHARED_SECRET` and gateway Worker
   secret `EDITOR_SHARED_SECRET`. Never put the value in either Wrangler file.
   On the gateway's first deployment, use Wrangler's `--secrets-file` option
   so the custom domain and encrypted secret become active atomically. On later
   rotations, use `wrangler secret put EDITOR_SHARED_SECRET`.
2. Generate a second random secret of at least 32 characters for lifetime
   counter reads. Store it as the gateway Worker secret `REPORT_SHARED_SECRET`
   and as the GitHub Actions secret `MCP_REPORT_TOKEN` in
   `manavmishra/ZSWebpage`. Never reuse `EDITOR_SHARED_SECRET`.
3. Deploy the website editor endpoint with the signed `noStore` contract.
4. From `mcp/scorer`, run `npm run deploy`.
5. Confirm the scorer deployment, then deploy the gateway. A first deployment
   must include `EDITOR_SHARED_SECRET` and `REPORT_SHARED_SECRET` in an
   ephemeral `.env` or JSON secrets file passed to
   `wrangler deploy --secrets-file`; remove that file immediately afterward.
   Existing deployments can run `npm run deploy` because Wrangler preserves
   encrypted secrets omitted from later uploads.
6. Check `https://mcp.zero-slop.ai/health`, initialize an MCP session, list
   tools, and exercise one clear draft plus one deliberately sloppy factual
   draft.
7. Read `GET https://mcp.zero-slop.ai/internal/counters` with the report token
   and confirm the initialization and call totals increased.
8. Do not announce the connector until the factual fixture returns a rewritten
   result with two independent model checks and the expected score reduction.

Do not deploy the gateway first. Its explicit `stored: false` requirement makes
that ordering fail closed, but it would leave all rewrites unavailable until
the website endpoint is current.

## Rollback

Each Worker is independently reversible:

```sh
wrangler deployments list
wrangler rollback VERSION_ID --message "rollback MCP release" --yes
```

Rollback the gateway first to remove the public behavior. Roll back the scorer
only if its health or parity check is at fault. The public tool schema and
fail-closed response shape should remain stable across rollbacks.
