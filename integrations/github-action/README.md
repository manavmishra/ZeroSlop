# Zero Slop documentation review

Review the Markdown files changed by a pull request. The default mode runs the
local writing scorer and adds a short report to the GitHub job summary. It does
not send drafts to an editor, change files, or post pull-request comments.

## Add to a workflow

The action runs on a GitHub-hosted Ubuntu runner with Python 3. It installs the
fixed `zero-slop@2.10.0` npm release in runner temporary storage. The scorer reads
Git blobs, not scripts or configuration from the pull request. Markdown must be
UTF-8; invalid text encoding fails the check instead of being silently replaced.

```yaml
name: Review documentation
on:
  pull_request:
    paths: ['**/*.md', '**/*.markdown']
permissions:
  contents: read
jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6
        with:
          python-version: '3.13'
      - uses: manavmishra/ZeroSlop/integrations/github-action@v2.10.0
        id: review
```

Use the release's full commit SHA instead of the version tag when your
organization requires immutable action references. Both comparison commits must
be available locally; the action does not fetch branches itself.

## Choose the review

| Input | Default | Meaning |
| --- | --- | --- |
| `mode` | `score` | `score` runs locally; `deslop` sends complete changed drafts to the hosted MCP editor. |
| `base-sha` | Event base | Full base commit SHA. Required when the event has no base, including a first push. |
| `head-sha` | Event head | Full head commit SHA. |
| `max-files` | `10` | Review up to 50 files. Remaining files appear as skipped. |
| `genre` | `general` | `general`, `social`, `email`, `research`, or `professional`. |
| `fail-above` | Empty | Optional local-score threshold from 0 to 100. A score of 25 passes a threshold of 25; 25.1 fails. |

Scores describe tracked writing patterns, not the probability that AI wrote a
document. A low score does not establish factual accuracy or replace a human
review. The action is advisory unless `fail-above` is set; unavailable checks
still fail the job so an outage cannot appear as a passed review.

Hosted editing requires `mode: deslop`. It sends each complete changed file, not
just the diff, to `https://mcp.zero-slop.ai/mcp`. The endpoint requires no account
or API key. Use it only for material your team has approved for that service.
Hosted edits are rejected for fork pull requests, and every mode rejects
`pull_request_target`.

```yaml
- uses: manavmishra/ZeroSlop/integrations/github-action@v2.10.0
  id: review
  with:
    mode: deslop
    max-files: '3'
    genre: professional
```

No edit is applied automatically. The report preserves the exact returned
result, including warnings and source-check failures. The action never treats
`rewritten_with_warnings` as a fully approved edit.

## Reports and limits

`report-path` is a JSON file in runner temporary storage. Local reports contain
filenames, scores, and outcomes. Hosted reports also contain the returned text
and review details. Nothing uploads that report automatically. If you add an
artifact-upload step, set access and retention appropriate for the documents.

The job summary excludes draft text, returned text, and detected phrases.
Repository filenames are escaped before appearing in its table. The `reviewed`
and `skipped` outputs make partial coverage visible.

The action skips symlinks, binary or empty content, files over 100,000 bytes, and
hosted drafts over 20,000 Unicode code points. It bounds each process and response, runs
files sequentially, and does not automatically replay an editing request after
a failure. It installs packages without lifecycle scripts and ignores checkout
npm configuration and private Zero Slop preferences.

See the [hosted-service privacy policy](https://zero-slop.ai/privacy/) and
[terms](https://zero-slop.ai/terms/) before enabling hosted editing.

## Validate and publish

```sh
node --test integrations/github-action/review.test.mjs
```

This subdirectory can be referenced directly by a workflow. A GitHub Marketplace
listing is a separate publication: copy this action into its own public
repository with `action.yml` at the root, verify the name is available, and
publish a release marked for Marketplace. The repository owner must accept the
Marketplace Developer Agreement. Packaging this action does not establish that
it has been listed.

References: [GitHub action metadata](https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax),
[Marketplace publication](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace).
