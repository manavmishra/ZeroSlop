# Listing status — 2026-09-07

Read-only checks of the actual OpenAI account dashboard and public directory pages.
No submission, resubmission, cancellation, publication, or account change was made.

| Channel | Observed status | Evidence |
| --- | --- | --- |
| OpenAI Plugins | **Review**, version **2.9.2**; name **Zero Slop**, subtitle **Edit AI-assisted writing** | Authenticated [Plugins dashboard](https://platform.openai.com/plugins). The version detail says “Viewing the review version. Only draft versions can be edited.” |
| Cursor Directory | Public **Zero Slop** page is live; links to the correct website and source repository; shows one MCP server and one skill | [Public listing](https://cursor.directory/plugins/zero-slop) |
| Skills.sh | Public **zero-slop** page is live; displayed 27 installs and first seen **Aug 22, 2026** | [Public listing](https://www.skills.sh/manavmishra/zeroslop/zero-slop) |
| Claude public plugin directory | Searches for **Zero Slop** and **slop**, without product filters, returned “No plugins for those filters” | [Public directory](https://claude.com/plugins). This does not establish whether a private submission exists. |

## OpenAI review

The submitted version is already in review. The dashboard did not show a
submission timestamp on the list, Info view, or submission summary. No rejection
or requested correction was visible. The release notes describe corrected MCP
metadata for aggregate usage recording, with editing behavior unchanged.

Leave version 2.9.2 unchanged while it is in review. OpenAI's documented process
is to await the review result; approval is followed by a separate publication
action. Review status is not approval or a public-directory listing.
[Review and approval guidance](https://developers.openai.com/plugins/deploy/app-review#review-and-approval)

## Public-listing scope

The Cursor evidence establishes a **cursor.directory** listing, not acceptance
into **cursor.com/marketplace**. The page loaded in the connected browser even
though an earlier automated fetch was rate-limited.

Skills.sh displayed **Gen Agent Trust Hub PASS**, **Socket WARN**, and **Snyk PASS**.
Its [Socket report](https://www.skills.sh/manavmishra/zeroslop/zero-slop/security/socket)
was dated **Sep 5, 2026, 10:34 AM** (timezone not shown), against commit
`5b9ef28f5807e5d8cbf577f1a514920e3970f116`. The single medium-severity finding
concerns `bench/version_compare.py`: it imports scorer code from caller-supplied
filesystem roots and invokes Git for benchmark metadata. The report does not
identify direct malicious logic in that wrapper.

Current package-scope checks:

- `npm pack --dry-run --ignore-scripts --json` for 2.9.2 returned 107 entries,
  with no `bench/` paths and no `version_compare.py`.
- `scripts/build_plugin.py` mirrors only `SKILL.md`, `references`, `scripts`,
  and `data`; the flagged file is absent from `skills/zero-slop`.

These checks establish exclusion from the npm payload and nested plugin skill
runtime. They do not clear the historical source-repository audit or establish
which files every third-party Git-based installer downloads.
