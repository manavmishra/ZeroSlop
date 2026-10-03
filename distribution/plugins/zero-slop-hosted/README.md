# Zero Slop Hosted

This package contains only the remote `deslop` MCP connector at
https://mcp.zero-slop.ai/mcp. It includes no skills, scripts, hooks, installers,
credential configuration, or local execution instructions. The separate Zero Slop
skill package is unchanged.

Calling the connector sends the supplied text, genre, and optional audience to
the hosted service. Scoring and source-preservation checks run server-side. The
result includes edited or unchanged text, before-and-after writing scores,
status, and review warnings. Scores are writing heuristics, not AI-authorship
probabilities; source checks are not a guarantee of factual accuracy.

Cloudflare hosts the service. Editing can use Cloudflare Workers AI and a bounded
OpenRouter fallback, so both services may process the supplied writing. Hosted
editing does not activate private learning or save local editing preferences.
The application processes writing in memory; service metrics, infrastructure
records, provider records, and the MCP host's conversation history have separate
retention policies. See [our privacy policy](https://zero-slop.ai/privacy/)
and [terms](https://zero-slop.ai/terms/) for processing and retention details.
Capacity limits or unavailable services can prevent an edit.

## Example requests and reported results

These endpoint observations illustrate possible outcomes, not guaranteed edits
or certification of Claude, mobile, or another MCP host.

### Professional update

Draft: "It is important to note that Maya reduced review time by 40% for Project
Northstar. The team will decide on Friday." Genre: professional.

Reported result: "Maya reduced review time by 40% for Project Northstar. The team
will decide on Friday." Status: `rewritten`; writing scores: 41.7 to 9.5;
`modelRequests: 1`. The stock opener was removed without changing the named
details, number, or date.

### Already-clear email

Draft: "The meeting starts at 10 am on Friday." Genre: email.

Reported result: unchanged; status: `already_clear`; writing scores: 9.5 to 9.5;
`factsPreserved: true`, `passedFinalChecks: false`, `modelRequests: 0`.

### Already-clear release note

Draft: "Version 3.2 fixes a crash on startup." Genre: professional.

Reported result: unchanged; status: `already_clear`; writing scores: 9.5 to 9.5;
`factsPreserved: true`, `passedFinalChecks: false`, `modelRequests: 0`.

Editing did not run for the two already-clear examples. Unchanged text is not a
completed editorial pass, and `factsPreserved` is not a factual-accuracy guarantee.

This directory is a review candidate, not evidence of publication or deployment.
Its manifest version follows the repository's release number; the live server
version is reported by https://mcp.zero-slop.ai/health. Support is available through
[GitHub issues](https://github.com/manavmishra/ZeroSlop/issues).
