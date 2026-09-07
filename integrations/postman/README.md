# Zero Slop in Postman

Import `zero-slop.postman_collection.json`. It contains requests to read the
OpenAPI contract, edit a synthetic draft, and check an invalid-input response.
The API uses free shared capacity and requires no API key.

Set Postman's request timeout to **75,000 ms**. Redirects are disabled on each
request; keep them disabled when sending drafts. Run the OpenAPI request first,
then choose **Send** on the draft you want to test. The collection contains no
automatic retry or publish step.

A `200` response can still contain a warning or an unchanged original. The
post-response script checks the 14 shared result fields and sets the local
`reviewRequired` boolean. It does not copy the draft or result into collection
variables. Review the returned `status` and `note`; passing these protocol tests
does not certify that the writing is ready to publish.

For `429`, respect `Retry-After` before a user-approved retry. After a timeout,
the service may still finish the original request. Do not automatically replay
the draft.

Postman can retain request bodies and responses in history, saved examples,
shared workspaces, or synced data. Those settings are separate from Zero Slop's
no-storage contract. Keep this collection synthetic when publishing it, and
check your workspace policy before entering private writing.

The importable collection is not a published Postman API Network listing.
Publication requires a publisher workspace and a final review for secrets and
private examples. See [Postman public API publication](https://learning.postman.com/docs/postman-api-network/showcase/publish/public-apis)
and [post-response tests](https://learning.postman.com/docs/tests-and-scripts/write-scripts/test-scripts/).

API reference: [OpenAPI contract](https://mcp.zero-slop.ai/openapi.json),
[source documentation](../../docs/rest-api.md).
