# Review a draft with Zero Slop in n8n

Import `zero-slop-review.workflow.json` into n8n. The manual workflow sends one
synthetic draft to the REST API, checks the response, and stops with text for a
person to review. It requires no API key and does not publish, email, or edit a
document.

Run the example before connecting your own input. The HTTP node uses
`POST https://mcp.zero-slop.ai/v1/deslop`, a 75,000 ms timeout, no redirects, and
no automatic retries. An HTTP error stops execution; a valid `200` result goes
through **Checks passed**. Drafts are limited to 20,000 Unicode code points and
the optional audience to 200; the complete UTF-8 JSON body must fit within 128 KiB.

That decision requires `factsPreserved: true` and either `already_clear`, or
`rewritten` with `passedFinalChecks: true`. Warnings and every other result go to
**Review warnings or keep original**. Both branches end at human review. Neither
is permission to publish automatically.

## Check n8n's storage settings

Zero Slop's no-storage contract does not control your n8n instance. n8n can keep
inputs and outputs in execution history, workflow definitions, pinned node data,
logs, or backups. This export disables saved successful, failed, and manual
executions, as well as saved node progress. Confirm those settings survive
import and meet your instance's policy before sending private writing.

Do not replace the synthetic code literal with a private draft: that would save
the draft inside the workflow definition even with execution-history saving
disabled. For real use, connect a source your team has approved, check its
retention settings, and keep pinning disabled. Do not attach an error workflow
that logs the full input or response.

If capacity is exhausted, read `Retry-After` and wait before deciding to retry.
A timed-out request may still finish on the service. The workflow deliberately
does not replay it.

The file is an importable workflow, not an accepted n8n Template Library listing.
Test the imported workflow in your n8n version before submission; local fixture
tests check its JSON, routing conditions, and request configuration, but do not
replace an actual n8n execution.

References: [HTTP Request node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest),
[workflow settings](https://docs.n8n.io/build/manage-workflows/configure-workflow-settings),
[API contract](https://mcp.zero-slop.ai/openapi.json).
