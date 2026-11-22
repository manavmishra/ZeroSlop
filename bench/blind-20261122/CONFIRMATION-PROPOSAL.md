# Final confirmation proposal — not launched

Status: proposed after development protocols 1 and 2. The sealed input and labels have not been inspected by this runner. Neither the prototype nor this protocol is final until the coordinator records its acceptance and exact candidate freeze. The development result of six ties and two current-release wins does not establish a gain for the bulk-execution prototype.

## Separate claims and experiments

1. **Portable skill comparison:** candidate, current Zero Slop 2.12.41, previous 2.12.40, pinned current avoid-ai-writing, humanizer, no-ai-slop, and bare-host control. All use the same host and common source/context/voice task. This tests the instructions and local assets actually executed. Gateway changes that the portable skill never exercises cannot be credited to this comparison.
2. **Same-host web-policy replay:** exact published versus candidate web prompts, API-native packets, and actual local response/protection validators. This has different available context from the portable skill experiment and must have separate results. It is not Workers AI, an actual deployed SaaS comparison, or proof of deployed free-provider quality.
3. **Gateway policy replay:** actual pinned routing and selection with real pinned offline scorer outputs and captured replayed editor responses. This requires an additional adapter; the web-prompt adapter alone does not exercise the published early `already_clear` gate or candidate routing. Local quota/signing stand-ins must be disclosed. No invented scorer results may be used as benchmark observations.

## Freeze before unsealing

Record exact commits and runtime hashes for all seven arms, final candidate code and instructions, scorer defaults, gateway/web policy revisions, CLI version, model, reasoning setting, schema, batch plan, timeouts, scheduler seed, evaluator/judge rubric, failure policy, input/label hashes and preregistration. Candidate tests and independent code review must pass first. Record which experiment actually exercises each implementation change.

The data owner should prepare an unlabeled input artifact after this freeze; labels remain separate from editors and judges. After opening the confirmation set, no candidate edits, threshold tuning or corpus repair may count as confirmation on that same set. Later changes require a fresh holdout. The existing development and failed-run artifacts remain immutable.

## Proposed inference plan

- Same existing Codex account, `gpt-6.2-astra`, reasoning `high`, schema-bound output, ephemeral sessions, ignored user config/rules and read-only sandbox for every arm.
- Sixty drafts per arm, four per batch: 15 batches × 7 arms = **105 calls**. Paired clean/slop variants stay together; four drafts represent two source groups. Check this from data-owner metadata after freeze rather than assume arbitrary input ordering is balanced.
- Common **600-second** subprocess budget per batch, at most two concurrent CLI calls. No automatic retries, model substitutions, shortened references, extra source support for one arm, or silent parser repairs.
- Prefer a deterministic round-robin batch-job scheduler over the pilot's whole-arm queue. Randomize arm order within each source-group block from a frozen seed, then run all 105 jobs through the same two-worker queue. This limits arm starvation if capacity ends. Record real queue order and timestamps. Do not claim simultaneous inference.
- Stage pinned tracked runtime paths only, with all required references retained. Each job gets a fresh isolated root and the same read-only `benchmark-input.json` containing only that batch's source/context/voice inputs. Optional offline helpers may consume it; no benchmark labels, other-arm outputs, personal profiles or prior conversations are staged. This is an equal convenience, not an instruction to bypass a workflow.
- Do not promise a filesystem read jail: continue auditing actual JSONL command traces for required reference reads and boundary violations.

Batch four preserves the measured high-reasoning development setting. Batch six would reduce calls to 70 and amortize reference reads, but introduces an untested batch size and larger within-call task; it is not the recommended confirmation default.

## Time and capacity estimate

Protocol 2 produced 48/56 rewrites. Twelve calls completed; two reached the common 240-second timeout. Recorded call durations totaled approximately 1,610 seconds. Linear scaling from eight to sixty drafts gives about **101 minutes at two workers**, but that estimate includes censored failures as though their work were complete. It is an optimistic floor, not a completion forecast.

Reserve **2–4 hours for seven-arm generation**, with substantial uncertainty from reference reading, helper calls, host queueing and the not-yet-frozen candidate. The strict inference ceiling is 105 × 600 = 63,000 call-seconds: approximately **8 hours 50 minutes** with two continuously occupied workers and one final odd job. The pilot's whole-arm scheduler could take **10 hours** in the all-timeout case because the seventh arm runs alone. The round-robin scheduler is recommended.

The twelve completed pilot calls reported 3,355,890 aggregate input tokens, including 2,840,448 cached input tokens, and 37,805 output tokens. Timeout calls had no completed-turn usage receipts. A 7.5× extrapolation is about **25.2 million aggregate input tokens and 284,000 output tokens**, excluding timeout consumption. A planning range of **25–40 million input tokens** is plausible but unvalidated. These are cumulative CLI usage counters across tool turns, not unique draft tokens. Cache availability is not guaranteed and cached use is not assumed free. Existing-account limits and monetary implications are unknown; do not invent a dollar estimate or buy capacity.

Two API-native web-policy arms at four cases per call add 30 calls. No inference pilot for those prompts has been run, so **20–60 minutes** is only a planning assumption; the common 600-second ceiling permits 2.5 hours. Full gateway replay can reuse captured provider responses locally when its actual request policy matches, but route differences must remain visible. Blinded judging and final checks require additional time and account capacity; they are not included in the seven-arm generation estimate.

## Failure and missing-output policy

Retain every raw prompt, response, JSONL trace, timeout, exit status, schema failure, source-span validation failure and timing receipt. A failed batch never receives invented output, inferred spans or a zero-harm certificate. Preserve successful independent batches from that arm.

Report intended and completed denominators by method and genre. Complete-case editorial results are explicitly conditional on available outputs. Report missingness separately, plus conservative bounds where useful: an unavailable positive is not a successful detection/removal; an unavailable clean case is not a demonstrated clean no-edit success. Precision from observed positive calls alone must not disguise incomplete coverage. Unobserved source fidelity is unknown, not zero context loss.

A full 60-case head-to-head claim requires complete matched coverage. If any arm is incomplete, publish neither a universal winner nor an all-method aggregate that mixes different drafts. Comparisons on an identically completed subset must identify the smaller subset and selection limitation. Do not pool the ultra development protocol, high development protocol, or a later rescue configuration into confirmation. If capacity/authorization ends, checkpoint all completed and active states and stop launching new jobs. A later recovery plan must be explicit; it does not erase first-attempt availability.

## Judging and publication boundary

Use source-only method-hidden packets with source facts, brief and voice constraints, exact source/output quotes for claimed harms, and separate private mappings. Freeze two fresh review passes with independently permuted positions; do not give judges method names, labels, scorer values or outputs from prior reviews. These remain model judgments, not human truth. Keep detection against synthetic author labels separate from source-fidelity and voice assessment.

Apply the existing preregistered source-group paired bootstrap, missing-value accounting, confusion matrices, paired discordances and scoped gain screen without weakening them. Keep the current-release comparison primary; report all comparator outcomes and failed gates. Sixty correlated drafts represent thirty source groups. Tiny genre counts are descriptive.

A same-host result cannot establish the deployed provider's quality. Actual provider contract tests and a small explicitly authorized fictional live check are separate release evidence; this plan makes no sixty-call production request. Publish only after the applicable code review, distribution/version checks, actual deploy verification and evidence-bound claims pass. No model keys, accounts, plans or paid capacity are created by this proposal.
