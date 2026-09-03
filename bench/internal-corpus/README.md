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
