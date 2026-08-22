# Benchmark harness

Everything needed to reproduce, contest, or extend the evaluation in
[EVALUATION.html](../EVALUATION.html).

- `examples.json` — the 50-draft corpus (25 LinkedIn, 8 blog, 5 newsletter,
  5 X/Twitter, 4 email, 3 research), each with the brief and ground-truth
  facts used for fidelity checking.
- `outputs/` — every method's rewrites, one file per method per half.
- `judging/` — blinded LLM-rating packets, the shuffle key, run-one scores
  (`scores-*.json`) and the replication scores (`rep2-scores-*.json`).
- `replication.py` — run-to-run tally, per-item agreement, Cohen's kappa,
  Wilson intervals. This is the script that moved the headline from 32/50 to
  a pooled 55/100.
- `aggregate.py`, `make_packets.py` — scorecard aggregation and packet
  construction (seeded shuffles, so packets rebuild identically).
- `objective-panel.json`, `judge-dimensions.json`, `replication.json` —
  computed results.
- `search-corpus/` — 18 anonymous, search-informed slop paraphrases across
  LinkedIn, X, email, blog, newsletter, and research, plus reproducible scores.

## Reproducing

```bash
python3 bench/replication.py          # agreement and pooled statistics
python3 bench/aggregate.py            # per-method scorecard
python3 bench/search-corpus/evaluate.py --check
```

## How the judging worked

No human raters took part. The 50 examples were divided into five packets of ten. For
each item, the packet contained the writing brief, original draft, factual inventory,
and four rewrites labeled A through D. A seeded shuffle hid which method produced each
rewrite.

Each pass used five fresh LLM judge runs from the same model family, one per packet. A
judge scored every rewrite from 1 to 10 on five labeled dimensions: human-likeness,
voice, fidelity, writing craft, and platform fit. It also marked possible fabrication
and selected the best and worst rewrite. A second set of five LLM runs reviewed the
same packets with the same label mapping. That produced two ratings for each of the 50
items, or 100 item-level selections in total.

The repository preserves the packets, shuffle key, raw scores, and aggregation code.
It does not preserve the exact judge model and version, inference settings, or full
evaluation prompt. The ratings therefore cannot be reproduced exactly from the public
harness. Treat them as a small, model-specific experiment rather than human evidence or
a general ranking of the tools.

## Adding a method

Drop `outputs/<yourmethod>_h1.json` and `_h2.json` (id → rewritten text),
add the name to the `METHODS` list in `make_packets.py`, and rebuild the
packets. To compare results with the existing ratings, document the model,
version, settings, and complete evaluation prompt used for the new blinded pass.

## Known limits

The drafts are synthetic, the evaluation used LLMs rather than human raters, and the
same model family was used for generation and judging. The corpus has only 50 items.
Winner agreement between the two passes was 52%, with a Cohen's kappa of 0.12. The
exact judge configuration and prompt are missing, and competing outputs were recreated
from published prompts rather than produced by the live tools.
