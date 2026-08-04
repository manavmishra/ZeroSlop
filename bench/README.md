# Benchmark harness

Everything needed to reproduce, contest, or extend the evaluation in
[EVALUATION.html](../EVALUATION.html).

- `examples.json` — the 50-draft corpus (25 LinkedIn, 8 blog, 5 newsletter,
  5 X/Twitter, 4 email, 3 research), each with the brief and ground-truth
  facts used for fidelity checking.
- `outputs/` — every method's rewrites, one file per method per half.
- `judging/` — blind judge packets, the shuffle key, run-one scores
  (`scores-*.json`) and the replication scores (`rep2-scores-*.json`).
- `replication.py` — run-to-run tally, per-item agreement, Cohen's kappa,
  Wilson intervals. This is the script that moved the headline from 32/50 to
  a pooled 55/100.
- `aggregate.py`, `make_packets.py` — scorecard aggregation and packet
  construction (seeded shuffles, so packets rebuild identically).
- `objective-panel.json`, `judge-dimensions.json`, `replication.json` —
  computed results.

## Reproducing

```bash
python3 bench/replication.py          # agreement and pooled statistics
python3 bench/aggregate.py            # per-method scorecard
```

## Adding a method

Drop `outputs/<yourmethod>_h1.json` and `_h2.json` (id → rewritten text),
add the name to the `METHODS` list in `make_packets.py`, rebuild the
packets, and judge them blind. Pull requests with new methods are welcome,
including ones that beat Zero Slop — that is what the harness is for.

## Known limits

Single model family for generation and judging; LLM judges rather than
human raters; a synthetic corpus we authored; and n = 50, which is small
enough that only large effects survive. The kappa of 0.12 measured here is
the reason every claim in the report carries its interval.
