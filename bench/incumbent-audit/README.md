# Pinned incumbent transfer audit

This audit runs the local detector from
[`conorbronsdon/avoid-ai-writing`](https://github.com/conorbronsdon/avoid-ai-writing)
at commit `40328bd292bc682d46010a6f9ac2cdbf4fb4ceca` on Zero Slop's frozen
38-item consensus editorial panel. It reports the incumbent's published score
gate and a gate selected on the development split, then evaluates that selected
gate once on the held-out split.

Reproduce it from a checkout at that exact commit:

```sh
python3 bench/incumbent-audit/evaluate.py \
  --avoid-root /path/to/pinned/avoid-ai-writing --write
```

The labels come from two method-hidden LLM editorial raters. This is a small
transfer check, not human field accuracy, authorship detection, or a universal
ranking.
