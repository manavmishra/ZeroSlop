# Research decisions — 22 November 2026

These sources motivate hypotheses and safeguards. They do not validate Zero Slop, supply new quality labels, or establish that the candidate outperforms competitors. Competitor revisions and the taxonomy audit are recorded separately in `competitor-delta-audit.md`.

## Measure editorial decisions, not presumed authorship

[AI Writers Have a Consistent Stylometric Footprint, but AI Editors Do Not](https://arxiv.org/abs/2608.27855v2) (22 September revision) finds different feature changes for generation and editing across its studied models and domains. Our inference: a stylistic feature is insufficient evidence that a passage is unnecessary or that its author used AI. Keep provenance datasets outside slop-quality accuracy claims. A low surface score cannot certify substantive, useful writing.

## Keep separate outcomes and test ranking stability

[SlopBench](https://arxiv.org/abs/2609.33905v1) (27 September) measures surface behaviors across multiple writing tasks. Its full model order changes with weighting, and additional checks do not confirm the middle ranking. Our decision: report detection, removal, clean edits, source fidelity, voice, completion and latency separately. Preserve the fixed native operating points and report paired uncertainty. Do not collapse these into a universal winner score or tune weights on the held-out examples.

## Preserve unchanged context explicitly

[HyperEdit](https://aclanthology.org/2026.findings-acl.22/) (July) treats instruction compliance and local fidelity as distinct editing requirements. It studies a trained architecture, which Zero Slop does not adopt. Our design inference is narrower: bind findings to exact source spans, make unchanged KEEP a valid result, require GAP questions instead of invented specifics, and verify the returned text. The paper's model gains cannot be credited to our prompt or validators.

## Voice needs its own assessment

[Can You Make It Sound Like You?](https://arxiv.org/abs/2604.24444v1) (April; preregistered study with 81 participants) reports that personal post-editing improves style similarity, while differences from unassisted writing remain. Its embedding measures and perceived authenticity are distinct. Our decision: blind reviewers assess voice alongside source facts; preserving numbers alone cannot demonstrate voice preservation. The synthetic benchmark's written voice constraints remain a narrow proxy, not a test of real authors' preferences.

## Treat public tell lists as contextual leads

[Signs of AI writing, and how to fix each one](https://hrih.si/articles/signs-of-ai-writing/) (3 November) is an editorial reference, not a labeled validation corpus. Its useful pattern families should be checked against existing coverage and legitimate uses before any rule is added. Do not import a blanket word ban, manufacture anecdotes, or delete substantive contrasts just because their shape appears in generated prose.

## Candidate and unresolved tradeoff

The candidate adds source-bound contextual review to ordinary hosted editing requests, including drafts below the numeric gate. It masks literal fenced blocks/comments in the optional meter and uses a fixed-window vocabulary measure. Those are implemented behaviors, not proven quality gains. Every ordinary hosted request now incurs model quota and possible latency; local character cleanup remains local.

A development-only exact-target-deletion probe found that the conservative claim guard blocks eight of twelve annotated filler deletions. The guard is retained. Findings and author questions can still surface a problem, but detection is not successful removal. The confirmation report must show this distinction, provider/validation failures, and any failed release gate. No held-out text was inspected to write this note.
