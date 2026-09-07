# 2.10.0 release notes

## Access paths

The npm CLI adds explicit hosted editing through the existing MCP service. REST
exposes the same pipeline and result schema at `/v1/deslop`, with a generated
OpenAPI 3.1.2 document. Neither transport adds a model or an automatic retry.
Local scoring and skill installation remain available without hosted editing.

GitHub Action, Raycast, Postman and n8n integration sources are included. Their
presence in this repository does not mean a marketplace has approved them.
See the [listing audit](listing-status-2026-09-07.md) and
[integration publication notes](../integrations/README.md).

## Benchmark continuity

This release does not change `scripts/slopscore.py`, `data/patterns.json`, or
`data/learned.json`. Their SHA-256 hashes match the benchmark records shipped
with 2.9.2. The [feature-ablation](../bench/feature-ablation/results.json),
[RAID+](../bench/raid-plus-corpus/results.json),
[version-comparison](../bench/version-comparison.json) and
[private-corpus](../bench/internal-corpus/results.json) records identify 2.10.0
as the release carrying that unchanged scorer.

Existing measurements and timing samples are retained, not presented as a new
performance run. No new model-quality, field-accuracy or speed claim is made.
The local regression checks verify the score vector and available private-corpus
aggregate replay without copying private source prose into the repository.
