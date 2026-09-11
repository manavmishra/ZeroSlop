# Reader review: implementation and release status

September 10, 2026 (Pacific). Local 2.12.0 candidate over
`0d866036b210b90e23fa9f7b4146316cf40c255e`. Not committed, published, deployed,
or installed into the user's existing global skill directories in this packet.

## Implemented

- Optional audience-review routing before editing: preview skim, two independent
  audience lenses, passage journals, notes-only recall and follow-up, revision
  comparison, and a source-preserving HTML report.
- Exact source plus audience/lens binding, terminal stopping, qualitative
  attention labels, explicitly retrospective fallback, escaped text and a
  restrictive content policy. The helper makes no model or network calls.
- Existing eight editing responsibilities and hosted one-request behavior
  retained. Simulated notes do not certify writing quality or factual accuracy.
- README, runtime reference, plugin mirror, single-file bundle, ZIP, npm
  packaging and version manifests updated locally to 2.12.0.
- Pinned First Reader capability comparison and regenerated chart. Thirty-two
  constructed offline component checks are recorded separately from human or
  model outcomes. No rewrite score was invented for a review-only tool.
- Production website source in `manavmishra/ZSWebpage`, base `101e25d`, includes
  the comparison and a responsive optional workflow animation marked
  **In development**. The retained `website/` snapshot remains undeployable.

## Verification

| Check | Result and scope |
| --- | --- |
| Main Python suite | 433 run: 432 passed, one skipped |
| Reader helper | 24 tests, included above |
| Historical-code compatibility | Eight additional tests passed; all seven code/data hashes match the old release |
| First Reader | 32/32 offline component fixtures; 10 comparison tests included in the main suite |
| CLI | 49/49 local contract tests |
| MCP/REST gateway | 79 Node tests plus 18 Vitest tests passed; TypeScript check passed |
| Scorer parity | Python/hosted scorer boundary checks passed |
| False positives | 12/12 regression samples passed; the existing lyric boundary remains documented |
| Packaging | All manifests agree; plugin, bundle, PyPI mirror and scorer mirror checks passed |
| npm dry run | 114 files, 235,901 bytes; helper/reference included; no benchmark source, output directory or bytecode shipped |
| Website | 705/705 tests; static build, source check, sitemap check and lint passed; three existing image warnings |
| Browser | Core report at 320/375/768/1440px; website 16 route/viewport/theme cases plus phone animation/reduced-motion checks passed |

The default shell's Node 20 failed the gateway prerequisite. Re-running with the
available Node 24.19 runtime passed. No dependency was installed and no billing
setting changed. Browser checks used emulated viewports, not physical devices.
Gateway and CLI tests used local/synthetic contracts, not paid production load.

A single local stress probe prepared and rendered 10,000 synthetic passages in
0.183 seconds, generating 7,315,753 HTML bytes without inference. This is a helper
capacity observation, not model latency, a production SLA, or a recommended
review size. The default host workflow limits review scope to 12 passages.

## Independent review

`/root/reader_candidate_review` initially requested changes: audience rebinding,
passage alignment on phones, contradictory reader-only instructions, oversized
JSON error handling, and narrow attention-strip collapse. Regression tests were
added and all five issues were fixed. The reviewer approved the changed core,
website and compatibility/documentation scope and inspected generated browser
screenshots. This was an agent review, not human validation.

Final core SHA-256:

```text
SKILL.md 37e94119dc60d315d5e0f342c6600ccd23361279375f2801bdf7678e58b1fb8e
references/reader-review.md d5cdf3ddb8301d70c0553b0f6fdac87ff02ec19cc77bbd71ddf0184d562e23dd
scripts/reader_review.py 1468797b4ea91af158f2f92f26aee0e04d875fab78149d0cf9ff11dbb365e74e
tests/test_reader_review.py 5252ee947e9e6452a9033a5ec8a6d02236bd164172608e21b37340204590b6b6
```

Historical benchmarks keep their original versions, dates and results. The
maintainer-only compatibility record accepts 2.11.6 evidence for the unchanged
scoring components in 2.12.0 only while every pinned file matches. It is not a
fresh measurement and does not evaluate the new reader workflow.

## Remaining delivery work

1. Obtain release authority, commit only the intended files, run normal CI,
   publish 2.12.0 and verify distribution receipts. Do not claim it is live now.
2. Import the verified release into the website, confirm runtime/download
   synchronization, then remove the development label and deploy through the
   existing guarded workflow. Do not deploy the snapshot.
3. Verify the installed host workflow in supported assistant environments and
   perform the matched reader/feedback study in [the research plan](../bench/first-reader/RESEARCH.md).
   The helper cannot prove context isolation; actual host-agent behavior,
   preference lift and field performance remain unmeasured.
4. Reconcile the private delivery checkpoint with Asana when its connector is
   available. The board is pending synchronization, not updated or closed.

There is no evidence here for a market-number-one or universal accuracy claim.
