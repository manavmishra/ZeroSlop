# Competitor delta audit — November 22, 2026

This is a selective audit of primary repositories, not a ranking of editing quality. It compares current default-branch commits with the exact August pins used in Zero Slop's existing capability audit and same-model replay. Those old outputs remain historical evidence and must not be relabeled as current competitor results.

## Pinned current sources

| Method | Prior pin | Current main | Meaningful change |
|---|---|---|---|
| Avoid AI Writing | `40328bd2` | `a5d6bae7c0d762dbcff74ca86c17a7ac9fee4151` (Nov 17) | 504 commits in the intervening history; substantial detector, context, preservation and workflow changes. Package version 3.39.0 plus unreleased main fixes. |
| Humanizer | `e2e92e7b` | `a32f24407364c74c812b43c15926d638bee1e072` (Nov 19) | 76 commits; now 4.0.0 plus unreleased main changes. Reorganized patterns and materially changed source-addition policy. |
| No AI Slop | `d30eddb9` | `000650b156983f5159695b441477f4e63b25dc85` (Sep 1) | Only one intervening commit touches the skill/evaluation files: simplified voice-trait planning and removed process/self-check ceremony. No new tell families in that delta. |
| Stop Slop | `8da1f030` | `8da1f030185bdfe8471220585162991eaeb970e9` | No change from the previously audited revision. Still useful as an established comparable skill, not a source of new updates. |

Repositories were selected for comparable public agent-skill format and established adoption. A GitHub metadata snapshot returned roughly 72k stars for Humanizer, 19k for Stop Slop, 14k for No AI Slop, and 6k for Avoid AI Writing. These signals help select coverage; they establish no quality ordering. This audit does not assess hosted commercial humanizers.

Immutable source links and raw file/notice hashes are in `zs-competitor-delta-audit-20261122.json`. Local snapshots are under `/private/tmp/zs-competitors-20261122/`.

## Findings worth testing in Zero Slop

**1. Give the scorer a source-aware view of prose.** Avoid AI Writing now has rendered-Markdown preprocessing, structural exclusions, source-offset tracking and safer linear fence/comment scanners. Its latest changes exempt distinct-term glossary entries from rhythm measurements while retaining repeated generic labels. Zero Slop's `score_text()` still uses `mask_quoted()` for weighted patterns; its structural fidelity gate and fallback protections do not automatically exclude code from the writing meter. This can preserve code correctly yet still score a quoted code specimen as slop. Test a shared offset-preserving prose mask, clean/dirty surrounding prose, matching and mismatched fences, unclosed fences, inline examples, HTML comments, glossary entries and worst-case scanning cost. Do not blindly mask every quotation from readability or every technical structure from all checks.

Source: [current detector](https://github.com/conorbronsdon/avoid-ai-writing/blob/a5d6bae7c0d762dbcff74ca86c17a7ac9fee4151/detector/patterns.js), [change history](https://github.com/conorbronsdon/avoid-ai-writing/blob/a5d6bae7c0d762dbcff74ca86c17a7ac9fee4151/CHANGELOG.md).

**2. Replace length-biased diversity as a hypothesis, not a borrowed claim.** Avoid AI Writing 3.37 switched from whole-document type-token ratio to a mean over 200-token windows after its own long human controls exposed false positives. Zero Slop still calculates whole-document distinct words / words and flags values below 0.40 once a document has 200 words. Evaluate windowed diversity with length-matched, genre-aware controls. The competitor's self-reported control results are not Zero Slop accuracy and do not establish a safe new production weight.

**3. Separate finding a phrase from justifying an edit.** Current Avoid AI Writing uses applicability/protection precedence and named editorial decision cards with edit, keep and missing-substance examples. Its deterministic taxonomy grew from 48 to 54 types. Seven added labels cover crowd contrasts, development-blog boilerplate, fake casual props, launch introductions, negation chains, negative parallelism and performed insight; acknowledgment-loop was removed from deterministic detection. Most overlap Zero Slop families already present. The important gap is conditional use: repeated rhetorical contrasts differ from an isolated technical distinction, and a reply that identifies the question it answers can be useful. Zero Slop still has a weighted acknowledgment-loop entry. Test that entry and broad contrast families for false positives before increasing their weight or copying new expressions.

Source: [editing contract](https://github.com/conorbronsdon/avoid-ai-writing/blob/a5d6bae7c0d762dbcff74ca86c17a7ac9fee4151/SKILL.md), [decision cards](https://github.com/conorbronsdon/avoid-ai-writing/blob/a5d6bae7c0d762dbcff74ca86c17a7ac9fee4151/references/patterns.md).

**4. Preserve actual informal register and reader context.** Current Humanizer explicitly keeps lowercase, abbreviations, fragments, anger and attempted-action wording in informal text. It adds stronger checks for replies that repeat background the recipient already has and for vague stand-ins such as “the part.” These are contextual review candidates. They should not become a universal ban on fragments, “let me know,” ordinary references to components, or genuine emotion. Zero Slop already has anti-overcorrection guidance; a useful candidate makes that guidance testable through no-edit controls and explicit reader context.

Source: [Humanizer 4.0 main instructions](https://github.com/blader/humanizer/blob/a32f24407364c74c812b43c15926d638bee1e072/SKILL.md), [change history](https://github.com/blader/humanizer/blob/a32f24407364c74c812b43c15926d638bee1e072/CHANGELOG.md).

**5. Do not import the current Humanizer source-addition policy.** Version 4.0 reverses its earlier no-addition rule and permits specific details known to be true; its voice section also permits adding a reaction where the writer would have one. This is a different task contract. Zero Slop should retain source-bound facts, experience and stance. A shared benchmark brief can fairly require every method to use only supplied facts, while documenting where that constraint narrows a competitor's native enrichment behavior. Do not characterize every true outside-source addition as a factual fabrication, but count unsupported-by-source additions against this benchmark's preservation requirement.

## Fair benchmark execution

Use the latest **pinned main** instructions, not an unpinned installed copy or old npm package. Label main-vs-stable differences. Avoid AI Writing requires its entire `references/patterns.md` for every mode; its official `SKILL.full.md` is a 158 KB self-contained option. Humanizer uses the root `SKILL.md`. No AI Slop needs `skills/no-ai-slop/SKILL.md` and `eval.md`. Stop Slop routes to its phrase, structure and example references. These paths and hashes are recorded in the machine-readable audit.

For deterministic detection, Avoid AI Writing's published CLI/Action gate now defaults to **more than six findings**, technical context, rendered-Markdown source. Do not substitute an arbitrary numeric score cutoff or treat its authorship-probability fields as editorial-quality accuracy. Keep full precision/recall curves alongside each native operating point. Humanizer, No AI Slop and Stop Slop are primarily host-model instructions; score their actual detection/edit outputs using the same model and task, not a nonexistent local detector.

Use source-grouped development and sealed test sets; a separate judge must see randomized output IDs without the method mapping. Keep generator settings and user scope equal, retain failures, and judge slop removed, unnecessary changes, source meaning, voice and latency separately. No current superiority claim is established by this audit.

## Licensing

All four repository roots carry MIT notices, with separate authors and copyright years. Preserve the relevant notices for substantial copied code or prose. Humanizer also credits Wikipedia's “Signs of AI writing”; a root MIT notice should not be assumed to relicense all underlying Wikipedia-derived wording. Prefer original implementation of general techniques and short attributed summaries; keep full competitor instruction snapshots local and bind them by immutable URL and hash rather than committing large text copies. No runtime code was changed by this audit. No installer, paid service or hosted editing API was used. One inspected dependency-free detector module was invoked locally on two synthetic diagnostic examples only.
