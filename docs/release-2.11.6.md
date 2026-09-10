# Zero Slop 2.11.6

This patch corrects the hosted-service operator in `TERMS.md` to **Garage
Capital Ventures LLC**, as confirmed by the owner on 10 September 2026. Terms
version 1.1 changes the operator name and effective date; other terms are
unchanged.

The skill, plugins, CLI, Python package and hosted manifests advance together.
There is no scorer, pattern, model, capacity-limit or runtime-logic change.

## Evidence provenance

- The private maintainer corpus was replayed locally with the existing evaluator.
  Its source hash and measurements are unchanged; no private prose is published.
- The 152-document feature-ablation vector was recomputed and validated against
  its recorded hash. Its candidate version advances to 2.11.6. The existing
  frozen LLM labels and research results are reused, not a new model study.
- The version-comparison runner was rerun against the original 2.7.7 baseline
  commit, `51d1d3bc055d59782a5d10c330bbaa63106e7d78`, with 12 alternating local
  timing runs. These measurements are machine-specific, not a speed guarantee.
- RAID+ provenance evidence must pass the existing pinned-source audit before
  this release publishes. Provenance labels are not editorial-quality labels.

The website imports the published release through its normal source-sync path.
An updated repository file alone does not establish that public Terms changed.
