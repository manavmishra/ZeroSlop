# Context-preserving local edits, November 22, 2026

Version 2.12.41 makes a bounded improvement to the installed editing workflow and
the local fallback used by the hosted MCP/API/CLI pipeline. It adds no model,
network request, telemetry field, training data export, or detector weight.

## Changes

- Remove a complete `In conclusion,` opening using the same capitalization helper
  as existing opening removal. Preserve mixed-case names such as iOS and eBPF.
- Keep the opening when exposing a lowercase word would require guessing whether
  it is an identifier or brand. Examples include `os.path.exists` and npm.
- Protect tilde-fenced code, longer fences, and unmatched fenced suffixes before
  applying local transformations. The Python and gateway implementations agree.
- Stop inventing conversations or a changed approach from unspecified insights.
  Stop naming an unspecified automated process as onboarding.
- Tell the installed assistant to preserve complete claim relationships, respect
  useful formality and terminology, and ask for missing substance in work documents.

The hosted model prompt remains unchanged. The hosted gateway receives the local
fallback fixes when this release deploys. The portable skill receives the expanded
editorial instructions when an installed copy is updated.

## Research findings and retained failures

Earlier research tested a qualifier-counting diagnostic. It caught 9 of 12 unsafe
rewrites but flagged 4 of 12 acceptable edits. It is excluded from production.
The initial wrapper prototype also corrupted iOS, eBay, and eBPF. This release
reuses the production helper and tests these names directly.

Independent review of the first release attempt found two more failures: editing
inside tilde fences and capitalizing lowercase identifiers. Both are retained as
regression tests. The second attempt protected fences and abstained on ambiguous capitalization,
but review found an older unconditional deletion could bypass that abstention.
The user authorized a third attempt. It removes those obsolete deletion rules
so an ambiguous opening stays intact, including when a contextual editor could
remove it. This conservative fallback can leave some filler for the assistant. The research routines were not copied into the runtime.

The existing claim guard remains conservative and incomplete. On a new challenge
set it flags 8/16 unsafe rewrites and 6/16 safe paraphrases. These are results of a
direct diagnostic probe, not full editing-pipeline outcomes. **This release does
not introduce a reliable semantic classifier or certify arbitrary paraphrases.**
Preserving names and figures alone cannot establish that a claim is unchanged.

## Fresh evaluation

A separate reviewer wrote and hashed 32 source/rewrite pairs and 12 full drafts
before inspecting the release implementation. The full drafts include engineering,
compliance, product, research, financial, technical, and commercial writing, with
explicit meaning, voice, and protected-content expectations.

The 12-draft local-fallback replay preserves every declared protected span, changes
none of the five clean controls, and is idempotent on all 12 drafts. Python and
TypeScript outputs match exactly. Two drafts receive additional complete-opening cleanup relative to 2.12.40.
The more conservative capitalization rule retains a frame in one financial draft
that the prior release removed; it avoids guessing how to expose a lowercase token. The fallback does not perform every suggested editorial
change or supply the missing substance in the two incomplete work documents.

A second set of six drafts was independently frozen before the authorized third
attempt. It also preserves every declared protected span, leaves all three clean
controls unchanged, and is idempotent in every case. These six are the fresh
unseen check for the final attempt; the earlier twelve are retained regressions.

These synthetic checks do not measure population accuracy, human-rated voice, or
improvement from the hosted model. Required meanings and tone also need contextual
review; literal-span checks are insufficient. The frozen expectations, source and
output text, runtime hashes, and first-attempt evidence are in
[`bench/context-release-20261122`](../bench/context-release-20261122/).

Reproduce from the repository root:

```sh
ZERO_SLOP_HOME=/tmp/zs-release-empty python3 bench/context-release-20261122/evaluate.py
mcp/gateway/node_modules/.bin/tsx bench/context-release-20261122/probe.ts
python3 -m unittest tests.test_context_preserving_rescue
```

The evaluator prints results without changing the stored evidence. The probe makes
no model or network request. Keep the original fixtures frozen; future tuning
requires a fresh unseen evaluation.

## Performance and regression checks

The full local Python suite completed 598 tests with one optional dependency test
skipped. The gateway check passed 154 Node tests and 65 Worker tests. Distribution
manifests, generated mirrors, scorer packaging, and release replay receipts passed.
The deterministic replay covers 152 surface and 114 regression documents; it adds
no new quality judgments.

Nine interleaved timings per fixture on this Mac measured 20,000-character prose
at a 13.982 ms median versus 11.799 ms for the baseline. The 20,000-character fenced
fixture measured 1.963 ms versus 9.501 ms, and an unmatched-fence 200,000-character
fixture measured 15.663 ms versus 103.283 ms. The small prose overhead is retained
as an explicit tradeoff for protection. These are synthetic in-process timings,
not load testing, production latency, or a field-scale reliability claim. See
`bench/context-release-20261122/performance.json`.

## Research basis

[October 2026 work on processing difficulty](https://arxiv.org/abs/2610.29162)
motivates examining dense noun stacks and long dependencies in context.
[ACL 2026 work on personal-style post-editing](https://aclanthology.org/2026.acl-long.2030/)
motivates preserving voice separately from reducing a writing score.
[Research on numerical misattribution](https://arxiv.org/abs/2610.38691)
motivates preserving a quantity's relationship to its metric and source.
These studies motivate design choices; they do not establish Zero Slop performance.

## Release verification

Publication must follow repository CI, independent exact-revision review, tagged
package publication, paired scorer/gateway deployment, and public health/version
verification. Live editing checks use fictional drafts only. GitHub workflow runs
are the authority for publication and deployment status, not this document.
