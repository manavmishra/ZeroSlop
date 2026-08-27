# Fresh method-hidden incumbent replay

This suite sends the same 18 deliberately obvious drafts through Zero Slop and
`avoid-ai-writing` with the same GPT model, reasoning level, batch size, and
Codex CLI. Each editing run starts without conversation history and cannot read
the other method.

Two fresh editorial review passes receive only the source and shuffled A/B
outputs. They use the same source-preservation, naturalness, clarity, and
mechanics rubric. A/B positions are reshuffled between passes. Deterministic
checks from both repositories run separately from the editorial review.

Run records bind the corpus, instructions, prompts, outputs, packets, mappings,
and reviews by SHA-256. The hosted model seed is not exposed. This is a small,
method-hidden regression comparison, not independent human field accuracy or a
universal ranking.

```sh
python3 bench/fresh-replay/run.py --method zero-slop --label "Zero Slop" \
  --root . --instruction SKILL.md --revision <revision> \
  --suite-dir bench/incumbent-blind-replay
python3 bench/fresh-replay/run.py --method avoid-ai-writing \
  --label avoid-ai-writing --root /path/to/pinned/incumbent \
  --instruction SKILL.md --revision <commit> \
  --suite-dir bench/incumbent-blind-replay
python3 bench/incumbent-blind-replay/judge.py
python3 bench/incumbent-blind-replay/evaluate.py \
  --avoid-root /path/to/pinned/incumbent --write
```
