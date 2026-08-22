# AIStoryHub corpus coverage audit

This audit probes Zero Slop against the public AIStoryHub Corpus of AI
Clichés. The source is pinned by version, date, entry count, and SHA-256 in
`source.json`.

The corpus is a taxonomy of tells, not a labeled set of human and machine
prose. The audit therefore reports how many supplied examples or unambiguous
literal terms produce at least one Zero Slop rule hit. It cannot measure
accuracy, precision, recall, rewrite quality, or authorship.

The source advertises a downloadable JSON file but does not state a
corpus-specific redistribution licence. The repository does not bundle the 758
entries. A maintainer fetches the pinned source only when running the audit:

```bash
python3 bench/aistoryhub-corpus/audit.py --fetch --check
python3 bench/aistoryhub-corpus/audit.py --fetch --write
```

To audit a file downloaded separately, replace `--fetch` with
`--source /path/to/ai-cliches-corpus.json`. A changed hash fails closed so a
new upstream release cannot silently alter the published result.
