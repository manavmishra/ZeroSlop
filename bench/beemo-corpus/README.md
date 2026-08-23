# Beemo paired-edit audit

This audit uses the public [Beemo](https://huggingface.co/datasets/toloka/beemo)
records without copying their text into this repository. Beemo pairs a model response
with an expert edit of that response and an independent human answer to the same
prompt. That makes it useful for testing whether Zero Slop's surface meter moves in
the expected direction after a human edit and whether it stays quiet on human prose.

It is not an accuracy benchmark. Beemo labels provenance and editing history, not
whether a passage is good, useful, factual, or stylistically sloppy. Its open-QA and
instruction-following categories also differ from Zero Slop's core business-writing
genres.

The source revision, row count, and field-specific license note are pinned in
`source.json`. The script refuses to fetch if the dataset's current revision no longer
matches that pin, rejects truncated or missing rows, and stores only aggregate results
and a content fingerprint.

```bash
python3 bench/beemo-corpus/audit.py --fetch --check
```

Use `--write` instead of `--check` only when intentionally refreshing the committed
result after a scorer or source-pin change.
