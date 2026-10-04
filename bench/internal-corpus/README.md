# Private maintainer corpus

This replay uses the nine populated examples in Manav's private Google Doc,
"Slop examples." The source stays under `~/.zero-slop/evals/` and is never
committed. `results.json` contains scores, finding names, counts, and hashes but
none of the submitted prose.

The set has no per-item rubric or clean controls. It is useful for catching
score drift and finding missed cases; it is not an accuracy benchmark.

```bash
python3 bench/internal-corpus/evaluate.py --check
```

When the document changes, export a fresh Markdown copy, replace the private
snapshot, inspect the change, and run the same command with `--write` to accept
the new hash and measurements.

Release checks use `results-<package-version>.json`, not `results.json`. Generate
each new release receipt with `--shared-only --out
bench/internal-corpus/results-<package-version>.json --write`, then check that
same path. This replays the admitted private source offline with private learned
preferences excluded and commits only aggregate findings, counts and hashes.
The evaluator refuses to overwrite an existing shared-only receipt; historical
receipts retain their original versions. CI validates the current receipt's
release and source/runtime pins even when the private prose is unavailable;
machines with the private source also recompute every measurement.
