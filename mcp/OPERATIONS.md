# Zero Slop MCP operations

This runbook covers the hosted connector at `https://mcp.zero-slop.ai/mcp`.
It documents operating targets and recovery steps, not contractual service
levels.

## Service shape

- A public TypeScript gateway validates MCP requests, enforces size and rate
  limits, and returns no-store responses.
- A private Python Worker runs the exact scorer shipped in the tagged skill.
- One signed request reaches the website editor, which makes at most one
  Workers AI call. A bounded local edit remains available if that call fails.
- Thirty-two Durable Object shards hold aggregate counters. Draft text is not
  written to logs, analytics, counters, or durable storage.

## Operating targets

| Measure | Target |
|---|---:|
| Gateway availability | 99.9% over 30 days |
| Health response, p95 | under 500 ms |
| `deslop` completion, p95 | under 36 seconds |
| Maximum request body | 128 KiB |
| Maximum draft | 20,000 characters |
| Model calls per edit | at most one |
| Unbounded retries | zero |

The deployment is free to return a source-preserving local edit with a warning
when the model is unavailable. It must not return an invented claim merely to
meet the writing target.

## Release

1. Run the root test suite and both Worker test suites.
2. Run `python3 mcp/scripts/sync_scorer.py --version X.Y.Z`.
3. Confirm every public manifest with
   `python3 scripts/check_distribution_manifests.py`.
4. Deploy the private scorer, then the gateway.
5. Call `/health`, initialize an MCP session, list tools, and run `deslop` on a
   fixture with names and numbers.
6. Tag the tested commit. The tag publishes the Registry record automatically.
7. Run `python3 scripts/check_release_surfaces.py --require-network --wait-seconds 600`.

## Alerts and recovery

Alert on sustained increases in HTTP 5xx responses, scorer-version mismatch,
model timeouts, local-fallback use, or rate-limit rejections. Aggregate metrics
may identify the failing stage; they must never include draft text.

If `/health` reports a scorer mismatch, redeploy the scorer named by the gateway
before accepting traffic. If the editor is unavailable, verify the signed
gateway-to-editor secret and Workers AI binding. Roll back by redeploying the
last tested tag to both Workers; never mix gateway and scorer versions.

If publication drifts, rerun the failed idempotent workflow. npm and MCP
Registry jobs check the published version before writing, so retries do not
create duplicate releases.
