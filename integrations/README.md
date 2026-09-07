# Zero Slop integrations

Use the same editing pipeline in the places where writing gets reviewed.

| Integration | What it does | Publication status |
| --- | --- | --- |
| [GitHub documentation review](github-action/README.md) | Checks changed Markdown locally by default; hosted edits require explicit opt-in. | Repository action source; Marketplace listing is separate. |
| [Raycast selected-text editor](raycast/README.md) | Previews selected text, edits through MCP, and waits for your copy or paste action. | Extension source; Store review and real-app acceptance tests remain required. |
| [Postman collection](postman/README.md) | Imports the contract and exercises a synthetic draft plus input rejection. | Importable collection; not published to the API Network. |
| [n8n review workflow](n8n/README.md) | Runs one manual edit and routes warnings to human review. | Importable workflow; not an accepted Template Library listing. |

The Action and Raycast integrations pin the `2.10.0` CLI release. Their hosted path uses
`https://mcp.zero-slop.ai/mcp`; it does not duplicate the editorial prompt or
introduce an independent rewriting service.

Postman and n8n use the REST adapter at `https://mcp.zero-slop.ai/v1/deslop`,
which calls the same hosted pipeline. Validate their examples without sending
a draft:

```sh
node --test integrations/github-action/review.test.mjs integrations/templates.test.mjs
node --experimental-strip-types --test integrations/raycast/test/review.test.ts
```
