# External model context

This directory records a clean-room rerun of the mechanical layer published by
[The Slop Index](https://github.com/hgaddipati1118/slop-index). It does not test
Zero Slop and is not part of the anti-slop instruction replay.

The upstream repository commits the raw generations and its scorer. At the
pinned revision in `results.json`, reproduce the result with:

```bash
python3 harness/score.py --run-id full-merged
python3 harness/rank_spread.py --run-id full-merged
```

No model APIs are called. The run rescored 19,928 preserved generations from 18
models against derived pre-ChatGPT human baselines. Lower is closer to that
baseline. The exact ranking is sensitive to axis weights, so the README treats
the chart as context and reports the bootstrap rank ranges rather than naming a
universal winner.
