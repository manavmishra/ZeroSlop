# First Reader source and component comparison

The source audit and 32 constructed fixture checks cover First Reader at
[`f56f4feb`](https://github.com/Shubhamsaboo/awesome-llm-apps/tree/f56f4febaac4eb869c2e98859e78612889913d3e/agent_skills/first-reader).
They test its documented scope and selected component contracts. They do not
measure reader reactions, editorial usefulness, recall accuracy, or rewrite quality.
No model was called and no human reader participated.

First Reader explicitly excludes rewriting. It appears in the capability matrix,
including its skim gate, staged passage feed, log-bound recall prompt, comments
page, and reader follow-up workflow. It receives no invented rewrite score and is
not added to historical rewriting panels. The existing competitors retain their
original pins and audit dates. Newly added reader capabilities are marked **not
assessed** for those older pins; this is different from **not documented**.

`source.json` pins all 13 files in the skill subtree plus the repository's
Apache-2.0 license by SHA-256. No upstream test suite or evaluation corpus exists
in that pinned subtree. `evaluate.py` is our own maintainer-only test harness;
upstream source is fetched on demand and is not redistributed in the MIT runtime.

```bash
python3 bench/first-reader/evaluate.py --fetch --source-root /tmp/first-reader-pinned
python3 bench/first-reader/evaluate.py --source-root /tmp/first-reader-pinned --check
python3 -m unittest discover -s tests -p 'test_first_reader_comparison.py'
python3 bench/make_charts.py --capabilities-only
python3 bench/make_charts.py --check
```

Only `--fetch` accesses the network. Every file hash is verified before importing
upstream modules. Fixtures use a temporary directory and block socket creation,
including loopback. The feed state machine is called directly: passage boundaries,
log and dwell refusals, quit position, and delayed state flush are exercised without
starting an HTTP server or waiting for a reading session. Other fixtures check the
skim view, trust counts, and the absence of unlogged draft content from recall and
follow-up prompts. Recorded logs are synthetic test input, not reader testimony.

`results.json` binds the source manifest and evaluator hashes and preserves each
check's result. Fetch once, then `--check` reproduces the same result offline.
Pillow is needed only to render the matrix, not for the fixture checks or chart
data validation. On this machine the initial default-Python fetch failed because
its CA bundle was not configured; setting `SSL_CERT_FILE=/etc/ssl/cert.pem` used
the installed trust store and passed without disabling certificate verification.

The HTTP transport, HTML rendering, hostile-input behavior, and isolation from
agents with filesystem access remain untested here. A log-only recall prompt does
not establish that a human would remember the same things the next day. Comparing
reader utility would require matched drafts and audience briefs, preserved model
and harness settings, independent ratings of useful source-grounded findings,
clean controls, and real reader validation. No claim of superiority follows from
capability presence or these passing software contracts.
