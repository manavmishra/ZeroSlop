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
    |-- 52 second end-to-end budget
    |-- bounded eight-role editorial pipeline
    |
    | service binding                    | HTTPS, HMAC, no-store
    v                                    v
private scorer Worker              production editor ladder
exact Zero Slop 2.8.7              same fixed roles as /try/
```

The split is deliberate. The TypeScript gateway owns the public protocol,
input schema, deadlines, release policy, and security headers. A private
Python Worker runs byte-for-byte copies of the shipped scorer modules. The
model-only roles use the measured provider ladder already used by `/try/`.
Calls run at temperature zero. Two binding-native backstops are appended to
every deployment, so a stale environment ladder cannot silently remove the
last editor or the second semantic verifier. The smaller backstop remains
available for editing but is excluded from semantic certification because it
failed the exact-token verifier fixture.

The gateway marks a rewrite fully checked only when all of these are true:

- deterministic reranking finds no dropped or invented facts;
- the final writing score is below 25;
- register and document-shape checks are clean;
- copy-desk and read-aloud passes were available;
- two verifier calls return the exact success token from different model
  rungs; and
- the fresh-eyes pass makes no unsafe or worse edit.

Missing an editorial target starts bounded repair. If the target still is not met,
the safest source-preserving edit comes back with a review warning instead of being
discarded. Only two conditions can return the source unchanged: the editing service
was unavailable, or every changed version failed the hard source check by adding or
dropping protected material. A clean source returns immediately after scoring and is
never sent to an editing model.

## Connect

Codex:

```sh
codex mcp add zero-slop --url https://mcp.zero-slop.ai/mcp
```

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
- The editor ladder requests zero-retention, no-training routing. Connector
  drafts and rewrites are not logged by Zero Slop. Operational logs contain
  only status, sizes, scores, timings, and provider metadata.
- The private scorer has no public route. It is reachable only through the
  Cloudflare service binding and cannot load a maintainer's private learning
  overlay.
- Tool input is treated as untrusted data. Callers cannot select a system
  prompt, provider URL, or model.
- Host and Origin validation, strict schemas, bounded packet sizes, per-call
  aborts, an end-to-end deadline, and a per-colocation capacity ceiling bound
  abuse and cost.
- Errors never include source text, generated text, stack traces, or provider
  credentials.

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
2. Deploy the website editor endpoint with the signed `noStore` contract.
3. From `mcp/scorer`, run `npm run deploy`.
4. Confirm the scorer deployment, then deploy the gateway. A first deployment
   must include `EDITOR_SHARED_SECRET` in an ephemeral `.env` or JSON secrets
   file passed to `wrangler deploy --secrets-file`; remove that file
   immediately afterward. Existing deployments can run `npm run deploy`
   because Wrangler preserves encrypted secrets omitted from later uploads.
5. Check `https://mcp.zero-slop.ai/health`, initialize an MCP session, list
   tools, and exercise one clear draft plus one deliberately sloppy factual
   draft.
6. Do not announce the connector until the factual fixture returns a rewritten
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
