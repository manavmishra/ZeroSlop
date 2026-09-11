# Reader-review design decisions

Research checked September 10, 2026 (Pacific). These are design constraints,
not evidence that Zero Slop predicts reader behavior. The implementation does
not change the scorer or claim a measured improvement in rewriting accuracy.

## Borrow the mechanism, test the claim

First Reader's pinned source motivates passage-limited context, independent
audience lenses, notes-only recall, and comments alongside the draft. Zero Slop
implements these mechanisms independently. It does not adopt forced reviewer
disagreement, artificial waiting as proof of human reading, or an unconditional
claim of offline inference. Its local helper performs no inference.

The current implementation explicitly allows agreement, uncertainty, a reader
stopping, and a retrospective fallback. It bounds the default review scope and
does not add reader calls to hosted editing. A hash binds notes to both the exact
draft and the audience configuration. That prevents accidental relabelling; it
cannot attest what a model actually saw.

## Primary research and its limits

- [Pohl et al., 2026](https://arxiv.org/abs/2607.28347): a preprint compares six
  models with 391 UK participants' belief updates. Persona traits did not
  consistently improve fidelity, and realistic initial stances mattered. This
  concerns persuasion in a controlled task, not editing or reading abandonment.
  Our inference: ground lenses in the user's actual task and do not invent
  demographic personas as if they represented people.
- [Zheng et al., 2023](https://arxiv.org/abs/2306.05685): MT-Bench/Chatbot Arena
  research identifies position, verbosity, and self-enhancement biases in model
  judging while finding useful agreement on its own tasks. That agreement rate
  is not Zero Slop accuracy. Our inference: hide method labels, counterbalance
  presentation order, and retain human evaluation before making superiority claims.

These papers' abstracts were reviewed for the claims above. Neither paper tests
Zero Slop or First Reader; neither validates an attention strip as human analytics.

## What would justify "better"?

Pre-register a matched evaluation before collecting responses:

1. Freeze source-grouped drafts and audience briefs across emails, launches,
   technical reference, research, and narrative. Include clean human-written
   controls and cases where brevity, repetition, or specialist vocabulary serve
   a purpose. Keep a held-out split that does not tune the instructions.
2. Compare Zero Slop's original editing workflow, its audience-review-assisted
   workflow, and First Reader's feedback on the same sources. Match host model,
   context policy, budgets, and prompts. Record tools, hashes, refusals, and cost.
3. Keep feedback usefulness separate from rewrite quality. First Reader receives
   no rewrite score. If an editor consumes either tool's feedback, freeze that
   editor and evaluate it as a separate assisted-editing condition.
4. Ask independent human raters to identify source-grounded, actionable findings,
   unsupported criticisms, missed ambiguities, and preserved meaning. Measure
   needless edits on clean controls and qualifier/fact corruption as primary
   harms, not just a lower score. Hide the tool name and counterbalance order.
5. Validate attention predictions against real task completion and passage-level
   reader feedback. Report disagreement and subgroup sample sizes. Choose sample
   size from the smallest useful effect and uncertainty targets before running;
   do not stop when a favorable ranking appears.
6. Publish methods, authorized examples, uncertainty intervals, latency/cost
   distributions, and negative results. Do not republish private drafts. A green
   software suite is not evidence of human preference or production scale.

Status: local contract tests and capability audit completed separately in this
directory. Model-assisted comparative outcomes and human validation are not run.
No "number one," field-accuracy, or human-preference claim is warranted yet.
